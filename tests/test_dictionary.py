"""Tests for unified dictionary interface (TODO #2 - Dictionary unification)."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from mitlesen.dictionary import BaseDictionaryInterface, BaseDictionary, SqliteDictionary
from mitlesen.db import SupabaseDictionary


class TestBaseDictionaryInterface:
    """Test the unified dictionary interface."""
    
    def test_interface_defines_required_methods(self):
        """Test that BaseDictionaryInterface defines all required abstract methods."""
        required_methods = [
            'search_by_lemma',
            'search_japanese_word',
            'close'
        ]
        
        for method in required_methods:
            assert hasattr(BaseDictionaryInterface, method)
            # Should be abstract
            assert getattr(getattr(BaseDictionaryInterface, method), '__isabstractmethod__', False)
    
    def test_cannot_instantiate_interface_directly(self):
        """Test that the interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseDictionaryInterface()


class TestBaseDictionaryImplementsInterface:
    """Test that BaseDictionary implements the interface correctly."""
    
    def test_inherits_from_interface(self):
        """Test that BaseDictionary inherits from BaseDictionaryInterface."""
        assert issubclass(BaseDictionary, BaseDictionaryInterface)
    
    def test_implements_all_interface_methods(self):
        """Test that BaseDictionary implements all interface methods."""
        interface_methods = [
            'search_by_lemma',
            'search_japanese_word', 
            'close'
        ]
        
        for method in interface_methods:
            assert hasattr(BaseDictionary, method)
            assert callable(getattr(BaseDictionary, method))


class TestSqliteDictionaryUnifiedInterface:
    """Test that SqliteDictionary works with the unified interface."""
    
    @patch('sqlite3.connect')
    def test_implements_interface(self, mock_connect):
        """Test that SqliteDictionary implements the unified interface."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        sqlite_dict = SqliteDictionary('/fake/path.db')
        
        # Should be instance of the interface
        assert isinstance(sqlite_dict, BaseDictionaryInterface)
        assert isinstance(sqlite_dict, BaseDictionary)
    
    @patch('sqlite3.connect')
    def test_search_by_lemma_method_signature(self, mock_connect):
        """Test that search_by_lemma has correct signature and return type."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {'id': '1', 'lemma': 'test', 'lang': 'en', 'meanings': '["definition"]'}
        ]
        mock_connect.return_value = mock_conn
        
        sqlite_dict = SqliteDictionary('/fake/path.db')
        
        # Test method exists and returns correct type
        result = sqlite_dict.search_by_lemma('test', 'en')
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], dict)
    
    @patch('sqlite3.connect')
    def test_search_japanese_word_method_signature(self, mock_connect):
        """Test that search_japanese_word has correct signature and return type."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            'id': '1', 'lemma': 'テスト', 'lang': 'ja', 'meanings': '["test"]'
        }
        mock_connect.return_value = mock_conn
        
        sqlite_dict = SqliteDictionary('/fake/path.db')
        
        # Test method exists and returns correct type
        word = {'base_form': 'テスト', 'pos': 'noun', 'text': 'テスト'}
        result = sqlite_dict.search_japanese_word(word)
        assert result is None or isinstance(result, dict)
    
    @patch('sqlite3.connect')
    def test_close_method_exists(self, mock_connect):
        """Test that close method exists and is callable."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        sqlite_dict = SqliteDictionary('/fake/path.db')
        
        # Should have close method
        assert hasattr(sqlite_dict, 'close')
        assert callable(sqlite_dict.close)
        
        # Should be able to call without error
        sqlite_dict.close()
        mock_conn.close.assert_called_once()


class TestSupabaseDictionaryUnifiedInterface:
    """Test that SupabaseDictionary implements the unified interface."""
    
    def test_implements_interface_methods(self):
        """Test that SupabaseDictionary implements all interface methods."""
        mock_client = Mock()
        supabase_dict = SupabaseDictionary(mock_client)
        
        interface_methods = [
            'search_by_lemma',
            'search_japanese_word',
            'close'
        ]
        
        for method in interface_methods:
            assert hasattr(supabase_dict, method)
            assert callable(getattr(supabase_dict, method))
    
    def test_search_by_lemma_implementation(self):
        """Test SupabaseDictionary search_by_lemma implementation."""
        mock_client = Mock()
        mock_table = Mock()
        mock_query = Mock()
        
        # Mock the query chain
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.ilike.return_value = mock_query
        mock_query.eq.return_value = mock_query
        
        # Mock response
        mock_response = Mock()
        mock_response.error = None
        mock_response.data = [
            {
                'id': '1',
                'lemma': 'test',
                'lang': 'en',
                'meanings': '["definition"]'
            }
        ]
        mock_query.execute.return_value = mock_response
        
        supabase_dict = SupabaseDictionary(mock_client)
        result = supabase_dict.search_by_lemma('test', 'en')
        
        # Verify the query was built correctly
        mock_client.table.assert_called_with('dictionaries')
        mock_table.select.assert_called_with('*')
        mock_query.ilike.assert_called_with('lemma', 'test')
        mock_query.eq.assert_called_with('lang', 'en')
        
        # Verify result format
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['lemma'] == 'test'
        assert result[0]['meanings'] == ["definition"]  # Should be parsed from JSON
    
    def test_search_japanese_word_implementation(self):
        """Test SupabaseDictionary search_japanese_word implementation."""
        mock_client = Mock()
        mock_table = Mock()
        mock_query = Mock()
        
        # Mock the query chain
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        # Mock successful response for first query (lemma_kana + pos)
        mock_response = Mock()
        mock_response.error = None
        mock_response.data = [
            {
                'id': '1',
                'lemma': 'テスト',
                'lang': 'ja',
                'pos': 'noun',
                'meanings': '["test"]'
            }
        ]
        mock_query.execute.return_value = mock_response
        
        supabase_dict = SupabaseDictionary(mock_client)
        word = {
            'base_form': 'テスト',
            'pos': 'noun',
            'text': 'テスト'
        }
        result = supabase_dict.search_japanese_word(word)
        
        # Should find a match on first attempt (lemma_kana + pos)
        assert result is not None
        assert isinstance(result, dict)
        assert result['lemma'] == 'テスト'
        assert result['meanings'] == ["test"]  # Should be parsed from JSON
    
    def test_close_method_no_op(self):
        """Test that close method exists and is a no-op for Supabase."""
        mock_client = Mock()
        supabase_dict = SupabaseDictionary(mock_client)
        
        # Should not raise any exception
        supabase_dict.close()


class TestDictionaryInterfaceUnification:
    """Test that both implementations can be used interchangeably."""
    
    @patch('sqlite3.connect')
    def test_polymorphic_usage(self, mock_connect):
        """Test that both dictionary types can be used polymorphically."""
        # Setup SQLite mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {'id': '1', 'lemma': 'test', 'lang': 'en'}
        ]
        mock_connect.return_value = mock_conn
        
        # Setup Supabase mock
        mock_client = Mock()
        mock_table = Mock()
        mock_query = Mock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.ilike.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_response = Mock()
        mock_response.error = None
        mock_response.data = [{'id': '2', 'lemma': 'test', 'lang': 'en'}]
        mock_query.execute.return_value = mock_response
        
        # Create both dictionary types
        sqlite_dict = SqliteDictionary('/fake/path.db')
        supabase_dict = SupabaseDictionary(mock_client)
        
        # Function that works with any dictionary implementing the interface
        def search_with_any_dict(dictionary: BaseDictionaryInterface, lemma: str):
            return dictionary.search_by_lemma(lemma)
        
        # Both should work with the same function
        sqlite_result = search_with_any_dict(sqlite_dict, 'test')
        supabase_result = search_with_any_dict(supabase_dict, 'test')
        
        # Both should return list of dictionaries
        assert isinstance(sqlite_result, list)
        assert isinstance(supabase_result, list)
    
    def test_interface_consistency(self):
        """Test that the unified interface provides consistent method signatures."""
        # Check that both implementations have the same method signatures
        sqlite_methods = {
            'search_by_lemma': SqliteDictionary.search_by_lemma,
            'search_japanese_word': SqliteDictionary.search_japanese_word,
            'close': SqliteDictionary.close
        }
        
        supabase_methods = {
            'search_by_lemma': SupabaseDictionary.search_by_lemma,
            'search_japanese_word': SupabaseDictionary.search_japanese_word,
            'close': SupabaseDictionary.close
        }
        
        # All methods should exist in both implementations
        assert set(sqlite_methods.keys()) == set(supabase_methods.keys())
        
        # All methods should be callable
        for method_name in sqlite_methods:
            assert callable(sqlite_methods[method_name])
            assert callable(supabase_methods[method_name])


class TestDictionaryUnificationSuccess:
    """Test that dictionary unification was successful (TODO #2 - COMPLETED)."""
    
    def test_common_interface_created(self):
        """Test that a common interface was created for dictionary operations."""
        from mitlesen.dictionary import BaseDictionaryInterface
        
        # Interface should exist and be abstract
        assert BaseDictionaryInterface is not None
        assert BaseDictionaryInterface.__abstractmethods__
        
        # Should define required methods
        required_methods = {'search_by_lemma', 'search_japanese_word', 'close'}
        assert required_methods.issubset(BaseDictionaryInterface.__abstractmethods__)
    
    def test_both_implementations_support_interface(self):
        """Test that both SQLite and Supabase implementations support the unified interface."""
        # SQLite implementation should inherit from interface
        assert issubclass(BaseDictionary, BaseDictionaryInterface)
        assert issubclass(SqliteDictionary, BaseDictionaryInterface)
        
        # Supabase implementation should implement all interface methods
        interface_methods = {'search_by_lemma', 'search_japanese_word', 'close'}
        supabase_methods = {method for method in dir(SupabaseDictionary) 
                          if not method.startswith('_') and callable(getattr(SupabaseDictionary, method))}
        assert interface_methods.issubset(supabase_methods)
    
    def test_api_unification_achieved(self):
        """Test that both implementations provide a unified API."""
        import inspect
        
        # Get method signatures for comparison
        sqlite_search_sig = inspect.signature(SqliteDictionary.search_by_lemma)
        supabase_search_sig = inspect.signature(SupabaseDictionary.search_by_lemma)
        
        # Parameter names should match (ignoring 'self')
        sqlite_params = list(sqlite_search_sig.parameters.keys())[1:]  # Skip 'self'
        supabase_params = list(supabase_search_sig.parameters.keys())[1:]  # Skip 'self'
        
        assert sqlite_params == supabase_params
        
        # Both should have the same return type annotations
        sqlite_return = sqlite_search_sig.return_annotation
        supabase_return = supabase_search_sig.return_annotation
        
        # Should both be List[Dict[str, Any]] or equivalent
        assert str(sqlite_return) == str(supabase_return)
    
    def test_redundancy_eliminated(self):
        """Test that code redundancy between implementations has been minimized."""
        import inspect
        
        # Both classes should implement the same interface methods
        sqlite_methods = {name for name, method in inspect.getmembers(SqliteDictionary, predicate=inspect.isfunction)
                         if not name.startswith('_')}
        supabase_methods = {name for name, method in inspect.getmembers(SupabaseDictionary, predicate=inspect.isfunction)
                           if not name.startswith('_')}
        
        # Should have core methods in common
        common_methods = sqlite_methods.intersection(supabase_methods)
        expected_common = {'search_by_lemma', 'search_japanese_word', 'close'}
        
        assert expected_common.issubset(common_methods)
    
    def test_backward_compatibility_maintained(self):
        """Test that existing Dictionary class is still available for backward compatibility."""
        import inspect
        from mitlesen.db import Dictionary
        
        # Original Dictionary class should still exist
        assert Dictionary is not None
        
        # Should still have original methods (both instance and class methods)
        original_methods = {'insert', 'exists', 'delete', 'fetch_all', 'fetch_by_id', 'to_dict'}
        dictionary_methods = {name for name, method in inspect.getmembers(Dictionary, 
                                                                         predicate=lambda x: inspect.ismethod(x) or inspect.isfunction(x))
                            if not name.startswith('_')}
        
        assert original_methods.issubset(dictionary_methods)