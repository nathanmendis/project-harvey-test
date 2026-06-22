import json
import logging
from django.utils import timezone
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from django.core.cache import cache
from google.api_core.exceptions import ResourceExhausted

from .graph import graph
from core.models.chatbot import Conversation, Message, GraphRun
from .tools_registry import tool_registry

logger = logging.getLogger("harvey")

class LLMResponse(BaseModel):
    response: str
    conversation_id: int
    title: str
    timestamp: str = ""


def _content_to_text(content):
    """Normalize AI content → plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        ).strip()
    return str(content)


def _save_chat(convo, user, user_input, ai_output):
    Message.objects.create(
        sender="user",
        message_text=user_input,
        conversation=convo,
        organization=user.organization,
    )
    ai_msg = Message.objects.create(
        sender="ai",
        message_text=ai_output,
        conversation=convo,
        organization=user.organization,
    )
    return ai_msg


def validate_and_sanitize_args(tool_name, args, user):
    """
    Validates and sanitizes user-edited arguments for sensitive tools.
    This acts as a foolproof security check on the backend.
    """
    if not isinstance(args, dict):
        raise ValueError("Invalid arguments format.")

    sanitized = {}
    if tool_name == "schedule_interview":
        from core.models.recruitment import Candidate
        from core.models.organization import User as OrgUser
        import pytz
        from django.utils.dateparse import parse_datetime

        # Check candidate
        candidate_id = args.get("candidate_id") or args.get("candidate")
        if not candidate_id:
            raise ValueError("Candidate ID is required.")
        try:
            candidate = Candidate.objects.get(id=int(candidate_id), organization=user.organization)
            sanitized["candidate_id"] = candidate.id
        except Exception:
            raise ValueError("Invalid Candidate specified.")

        # Check interviewer
        interviewer_id = args.get("interviewer_id") or args.get("interviewer")
        if not interviewer_id:
            raise ValueError("Interviewer ID is required.")
        try:
            interviewer = OrgUser.objects.get(id=int(interviewer_id), organization=user.organization)
            sanitized["interviewer_id"] = interviewer.id
        except Exception:
            raise ValueError("Invalid Interviewer specified.")

        # Check datetime
        dt_str = args.get("date_time") or args.get("date")
        if not dt_str:
            raise ValueError("Date/Time is required.")
        dt = parse_datetime(str(dt_str))
        if not dt:
            raise ValueError("Invalid Date/Time format. Use YYYY-MM-DD HH:MM.")
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, pytz.timezone("Asia/Kolkata"))
        sanitized["date_time"] = dt.isoformat()

        sanitized["interview_type"] = args.get("interview_type", "online")
        sanitized["location"] = args.get("location", "")
        sanitized["description"] = args.get("description", "")

    elif tool_name in ["send_email", "send_email_tool"]:
        sanitized["recipient_email"] = str(args.get("recipient_email", args.get("recipient", ""))).strip()
        if "@" not in sanitized["recipient_email"]:
            raise ValueError("Invalid recipient email address.")
        sanitized["subject"] = str(args.get("subject", "HR Update")).strip()
        sanitized["body"] = str(args.get("body", "")).strip()
        if not sanitized["body"]:
            raise ValueError("Email body cannot be empty.")

    elif tool_name == "apply_leave":
        from django.utils.dateparse import parse_date
        start_date = parse_date(str(args.get("start_date")))
        end_date = parse_date(str(args.get("end_date")))
        if not start_date or not end_date:
            raise ValueError("Invalid start or end date format.")
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date.")

        sanitized["start_date"] = start_date.isoformat()
        sanitized["end_date"] = end_date.isoformat()
        sanitized["leave_type"] = args.get("leave_type", "sick")
    else:
        # Fallback for general tools
        sanitized = args

    return sanitized


def generate_llm_reply(prompt: str, user, conversation_id=None, request=None, action=None, arguments=None):
    # 1. Check for Rate Limit Block
    if cache.get(f"chat_block_{user.id}"):
        return LLMResponse(response=" System is cooling down due to high traffic. Please try again in 60 seconds.", conversation_id=0, title="Error")

    if conversation_id:
        try:
            convo = Conversation.objects.get(id=conversation_id, user=user)
        except Conversation.DoesNotExist:
            return LLMResponse(response=" Conversation not found.", conversation_id=0, title="Error")
    else:
        # Create NEW conversation
        # Generate a title based on the first few words of the prompt
        title = " ".join(prompt.split()[:4]) + "..." if prompt else "New Chat"
        convo = Conversation.objects.create(
            organization=user.organization,
            user=user,
            title=title,
        )

    run = GraphRun.objects.create(
        conversation=convo,
        user=user,
        input_text=prompt or f"Action: {action}",
        status="running",
    )

    thread_id = f"convo-{convo.id}"

    config = RunnableConfig(
        configurable={"thread_id": thread_id},
        metadata={"graph_run_id": str(run.id)},
    )

    try:
        # Check if this is an approval/cancellation action from the Human-in-the-Loop check
        if action:
            checkpoint = graph.get_state(config=config)
            state_values = checkpoint.values if checkpoint else {}
            pending_tool = state_values.get("pending_tool")

            if not pending_tool:
                run.status = "error"
                run.error_message = "No pending action found."
                run.save()
                return LLMResponse(response="⚠️ No pending action found to confirm.", conversation_id=convo.id, title=convo.title)

            if action == "cancel_tool":
                # User requested a Redo/Cancel: clean graph state
                graph.update_state(config=config, values={"pending_tool": None, "requires_approval": False})
                run.status = "success"
                run.output_text = "I've cancelled that request."
                run.save()
                ai_msg = _save_chat(convo, user, "Cancel action", "I've cancelled that request.")
                return LLMResponse(
                    response="I've cancelled that request.",
                    conversation_id=convo.id,
                    title=convo.title,
                    timestamp=ai_msg.timestamp.isoformat()
                )

            elif action == "approve_tool":
                # Sanitize and validate arguments before execution
                try:
                    validated = validate_and_sanitize_args(pending_tool["name"], arguments, user)
                    pending_tool["args"] = validated
                except ValueError as ve:
                    run.status = "error"
                    run.error_message = str(ve)
                    run.save()
                    return LLMResponse(response=f"⚠️ Validation failed: {ve}", conversation_id=convo.id, title=convo.title)

                # Set requires_approval to False so graph continues to TOOL node
                graph.update_state(config=config, values={
                    "pending_tool": pending_tool,
                    "requires_approval": False
                })
                # Resume execution
                result = graph.invoke(None, config=config)
            else:
                run.status = "error"
                run.error_message = f"Invalid action: {action}"
                run.save()
                return LLMResponse(response="⚠️ Invalid action request.", conversation_id=convo.id, title=convo.title)
        else:
            # Standard prompt invocation
            checkpoint = graph.get_state(config=config)
            prev_state = checkpoint.values if checkpoint else {}

            prev_msgs = prev_state.get("messages", [])[-10:]

            state_input = {
                "messages": prev_msgs + [HumanMessage(content=prompt)],
                "user_id": user.id,
                "summary": prev_state.get("summary"),
                "pending_tool": prev_state.get("pending_tool"),
                "trace": prev_state.get("trace", []),
            }

            logger.debug(f"Graph invoke. User: {user.username}, Msg Count: {len(state_input.get('messages', []))}")
            result = graph.invoke(state_input, config=config)

        # Process the result of the invocation (either initial or resumed)
        msgs = result.get("messages", [])
        last_msg = msgs[-1].content[:50] + "..." if msgs else "No messages"
        logger.debug(f"Graph completed. Keys: {list(result.keys())}, Last output: {last_msg}")

        pending_tool = result.get("pending_tool")
        requires_approval = result.get("requires_approval", False)
        final_text = ""

        # If a tool needs execution, check if it's currently flagged for approval
        if pending_tool and not requires_approval:
            tool_name = pending_tool.get("name")
            tool_args = pending_tool.get("args", {})
            tool_func = tool_registry.get(tool_name)

            logger.info(f"Running Tool: {tool_name}")
            if tool_func:
                tool_args["user"] = user
                try:
                    raw = tool_func(**tool_args)
                    data = json.loads(raw)
                    tool_msg = data.get("message", "Action completed.")
                    result["messages"].append(ToolMessage(tool_call_id=pending_tool["id"], content=tool_msg))
                    result["pending_tool"] = None
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    result["messages"].append(AIMessage(content=f"⚠️ Tool failed: {e}"))
            else:
                result["messages"].append(AIMessage(content=f"⚠️ Unknown tool '{tool_name}'"))

        # --- FINAL AGGREGATION ---
        all_result_msgs = result.get("messages", [])
        
        last_human_idx = -1
        for i in range(len(all_result_msgs) - 1, -1, -1):
            if isinstance(all_result_msgs[i], HumanMessage):
                last_human_idx = i
                break
                
        if last_human_idx != -1:
            new_msgs = all_result_msgs[last_human_idx + 1:]
        else:
            new_msgs = [all_result_msgs[-1]] if all_result_msgs else []
        
        has_ai_message = any(isinstance(msg, AIMessage) and msg.content for msg in new_msgs)
        
        parts = []
        for msg in new_msgs:
            if isinstance(msg, AIMessage):
                txt = _content_to_text(msg.content)
                if txt:
                     parts.append(txt)
            elif isinstance(msg, ToolMessage) and not has_ai_message:
                txt = _content_to_text(msg.content)
                if txt:
                     parts.append(txt)
        
        if parts:
            final_text = "\n\n".join(parts)
        else:
            final_text = "Action completed."

        # Intercept tool configuration to display interactive approval cards to the user
        if pending_tool and requires_approval:
            args_json = json.dumps(pending_tool.get("args", {}))
            final_text = f"[Pending Approval: {pending_tool['name']}|{args_json}]"

        # Save DB run metadata
        run.status = "success"
        run.output_text = final_text
        run.trace = result.get("trace", [])
        run.finished_at = timezone.now()
        run.save()

        # Save chat history
        ai_msg = _save_chat(convo, user, prompt or f"Action: {action}", final_text)

        return LLMResponse(
            response=final_text,
            conversation_id=convo.id,
            title=convo.title,
            timestamp=ai_msg.timestamp.isoformat()
        )

    except ResourceExhausted:
        logger.warning(f"Rate Limit Hit for user {user.id}")
        cache.set(f"chat_block_{user.id}", True, timeout=60)
        
        run.status = "error"
        run.error_message = "Rate Limit Exceeded (429)"
        run.save()
        
        return LLMResponse(
            response=" API Rate limit reached. System is cooling down. Please wait 60 seconds.",
            conversation_id=convo.id if locals().get('convo') else 0,
            title="Error"
        )

    except Exception as e:
        logger.error(f"Graph ERROR: {repr(e)}", exc_info=True)

        run.status = "error"
        run.error_message = str(e)
        run.finished_at = timezone.now()
        try:
            run.save()
        except Exception as db_err:
            logger.error(f"Failed to update GraphRun status: {db_err}")

        return LLMResponse(
            response="⚠️ Something went wrong. Try again!",
            conversation_id=convo.id if locals().get('convo') else 0,
            title="Error"
        )

