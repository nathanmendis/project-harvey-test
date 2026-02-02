import pytest
from unittest.mock import MagicMock, patch
from core.tools.search_tool import search_knowledge_base
from core.tools.policy_search_tool import search_policies
from core.models.recruitment import Candidate
from core.models.policy import Policy

# We mock the vector store to verify the correct filters are passed
# This ensures our logic enforces the separation, independent of the DB state

@pytest.fixture
def mock_vector_store():
    with patch('core.tools.search_tool.get_vector_store') as mock_get:
        mock_store = MagicMock()
        mock_get.return_value = mock_store
        
        # We need to return some dummy results so the tool doesn't just say "No results" immediately
        # stored in a way we can inspect if needed, but mostly we care about the call args
        mock_doc = MagicMock()
        mock_doc.page_content = "Some content"
        mock_doc.metadata = {"source": "Test", "type": "candidate"}
        mock_store.similarity_search.return_value = [mock_doc]
        
        yield mock_store

@pytest.fixture
def mock_policy_vector_store():
    with patch('core.tools.policy_search_tool.get_vector_store') as mock_get:
        mock_store = MagicMock()
        mock_get.return_value = mock_store
        
        mock_doc = MagicMock()
        mock_doc.page_content = "Policy content"
        mock_doc.metadata = {"source": "Policy", "type": "policy"}
        mock_store.similarity_search.return_value = [mock_doc]
        
        yield mock_store

def test_search_knowledge_base_filters_candidates(mock_vector_store):
    """
    Test that search_knowledge_base applies the correct doc_type filter
    for candidates and job roles, excluding policies.
    """
    query = "Steve developer"
    search_knowledge_base.invoke({"query": query})
    
    # Verify similarity_search was called
    args, kwargs = mock_vector_store.similarity_search.call_args
    
    # Check the filter argument
    assert 'filter' in kwargs, "Filter argument should be present"
    filter_arg = kwargs['filter']
    
    # Expecting: {'doc_type': {'$in': ['candidate', 'job_role']}}
    assert 'doc_type' in filter_arg
    assert filter_arg['doc_type'] == {'$in': ['candidate', 'job_role']}

def test_search_policies_filters_policies(mock_policy_vector_store):
    """
    Test that search_policies applies the correct doc_type filter
    strictly for hr_policies.
    """
    query = "Leave policy"
    search_policies.invoke({"query": query})
    
    # Verify similarity_search was called
    args, kwargs = mock_policy_vector_store.similarity_search.call_args
    
    # Check the filter argument
    assert 'filter' in kwargs
    filter_arg = kwargs['filter']
    
    # Expecting: {'doc_type': 'hr_policy'} (wrapped in checking user org usually, but base filter is strict)
    # The tool code: filter_args = {"filter": {"doc_type": "hr_policy"}}
    
    doc_type_filter = filter_arg.get('doc_type')
    assert doc_type_filter == "hr_policy"
