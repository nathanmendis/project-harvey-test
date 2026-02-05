from django.test import TestCase
from unittest.mock import MagicMock, patch
from core.ai.rag.tools.search_tool import search_knowledge_base
from core.ai.rag.tools.policy_search_tool import search_policies

class TestRAGFiltering(TestCase):
    
    @patch('core.ai.rag.tools.search_tool.get_vector_store')
    def test_search_knowledge_base_filters_candidates(self, mock_get_store):
        """
        Test that search_knowledge_base applies the correct doc_type filter
        for candidates and job roles, excluding policies.
        """
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store
        
        mock_doc = MagicMock()
        mock_doc.page_content = "Some content"
        mock_doc.metadata = {"source": "Test", "type": "candidate"}
        mock_store.similarity_search.return_value = [mock_doc]

        query = "Steve developer"
        search_knowledge_base.invoke({"query": query})
        
        # Verify similarity_search was called
        args, kwargs = mock_store.similarity_search.call_args
        
        # Check the filter argument
        self.assertIn('filter', kwargs, "Filter argument should be present")
        filter_arg = kwargs['filter']
        
        # Expecting: {'doc_type': {'$in': ['candidate', 'job_role']}}
        self.assertIn('doc_type', filter_arg)
        self.assertEqual(filter_arg['doc_type'], {'$in': ['candidate', 'job_role']})

    @patch('core.ai.rag.tools.policy_search_tool.get_vector_store')
    def test_search_policies_filters_policies(self, mock_get_store):
        """
        Test that search_policies applies the correct doc_type filter
        strictly for hr_policies.
        """
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store
        
        mock_doc = MagicMock()
        mock_doc.page_content = "Policy content"
        mock_doc.metadata = {"source": "Policy", "type": "policy"}
        mock_store.similarity_search.return_value = [mock_doc]

        query = "Leave policy"
        search_policies.invoke({"query": query})
        
        # Verify similarity_search was called
        args, kwargs = mock_store.similarity_search.call_args
        
        # Check the filter argument
        self.assertIn('filter', kwargs)
        filter_arg = kwargs['filter']
        
        doc_type_filter = filter_arg.get('doc_type')
        self.assertEqual(doc_type_filter, "hr_policy")
