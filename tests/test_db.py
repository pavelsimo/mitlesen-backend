"""Tests for refactored database models (TODO #4 - COMPLETED)."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from mitlesen.db import BaseSupabaseModel, Video, Genre, Series, SeriesGenre, get_supabase_client


class TestBaseSupabaseModel:
    """Test the new BaseSupabaseModel class."""
    
    def test_abstract_methods_defined(self):
        """Test that BaseSupabaseModel defines the required abstract methods."""
        # Should not be able to instantiate BaseSupabaseModel directly
        with pytest.raises(TypeError):
            BaseSupabaseModel()
    
    def test_common_methods_available(self):
        """Test that BaseSupabaseModel provides common methods."""
        # Check that the base class has the expected methods
        base_methods = [method for method in dir(BaseSupabaseModel) if not method.startswith('__')]
        
        expected_methods = [
            '_insert_with_duplicate_handling',
            '_fetch_by_field',
            '_fetch_by_fields', 
            '_fetch_all',
            '_exists_by_field',
            '_get_client',
            'get_table_name',
            'from_row',
            'to_dict'
        ]
        
        for expected_method in expected_methods:
            assert expected_method in base_methods, f"Missing method: {expected_method}"
    
    def test_get_supabase_client_function(self):
        """Test the get_supabase_client function."""
        with patch.dict('os.environ', {'SUPABASE_URL': 'test-url', 'SUPABASE_KEY': 'test-key'}):
            with patch('supabase.create_client') as mock_create:
                mock_client = Mock()
                mock_create.return_value = mock_client
                
                client = get_supabase_client()
                
                mock_create.assert_called_once_with('test-url', 'test-key')
                assert client is mock_client


class TestRefactoredModels:
    """Test that models properly inherit from BaseSupabaseModel."""
    
    def test_all_models_inherit_from_base(self):
        """Test that all models inherit from BaseSupabaseModel."""
        models = [Video, Genre, Series, SeriesGenre]
        
        for model in models:
            assert issubclass(model, BaseSupabaseModel), f"{model.__name__} should inherit from BaseSupabaseModel"
    
    def test_table_names_implemented(self):
        """Test that all models implement get_table_name."""
        expected_tables = {
            Video: 'videos',
            Genre: 'genres', 
            Series: 'series',
            SeriesGenre: 'series_genres'
        }
        
        for model, expected_table in expected_tables.items():
            assert model.get_table_name() == expected_table
    
    def test_from_row_methods_implemented(self):
        """Test that all models implement from_row."""
        # Test Video.from_row
        video_row = {
            'id': 1, 'title': 'Test Video', 'youtube_id': 'abc123',
            'is_premium': False, 'transcript': 'test', 'language': 'en'
        }
        video = Video.from_row(video_row)
        assert video.id == 1
        assert video.title == 'Test Video'
        assert video.youtube_id == 'abc123'
        
        # Test Genre.from_row
        genre_row = {'id': 1, 'name': 'Action', 'created_at': '2023-01-01'}
        genre = Genre.from_row(genre_row)
        assert genre.id == 1
        assert genre.name == 'Action'
        
        # Test Series.from_row
        series_row = {'id': 1, 'title': 'Test Series', 'created_at': '2023-01-01'}
        series = Series.from_row(series_row)
        assert series.id == 1
        assert series.title == 'Test Series'
        
        # Test SeriesGenre.from_row
        sg_row = {'series_id': 1, 'genre_id': 2, 'created_at': '2023-01-01'}
        sg = SeriesGenre.from_row(sg_row)
        assert sg.series_id == 1
        assert sg.genre_id == 2
    
    def test_to_dict_methods_implemented(self):
        """Test that all models implement to_dict."""
        video = Video(1, 'Test', 'abc123', False, 'transcript', 'en')
        video_dict = video.to_dict()
        assert video_dict['id'] == 1
        assert video_dict['title'] == 'Test'
        assert video_dict['youtube_id'] == 'abc123'
        
        genre = Genre(1, 'Action')
        genre_dict = genre.to_dict()
        assert genre_dict['id'] == 1
        assert genre_dict['name'] == 'Action'


class TestBaseSupabaseModelFunctionality:
    """Test BaseSupabaseModel functionality."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock Supabase client."""
        client = Mock()
        table = Mock()
        client.table.return_value = table
        return client, table
    
    def test_insert_with_duplicate_handling(self, mock_client):
        """Test _insert_with_duplicate_handling method."""
        client, table = mock_client
        
        # Mock successful insert
        table.insert.return_value.execute.return_value = Mock(
            error=None,
            data=[{'id': 1, 'name': 'Test Genre', 'created_at': '2023-01-01'}]
        )
        
        with patch.object(Genre, '_get_client', return_value=client):
            result = Genre._insert_with_duplicate_handling({'name': 'Test Genre'}, ['name'])
            
            assert result is not None
            assert result.name == 'Test Genre'
            table.insert.assert_called_once_with({'name': 'Test Genre'})
    
    def test_fetch_by_field(self, mock_client):
        """Test _fetch_by_field method."""
        client, table = mock_client
        
        # Mock successful fetch
        table.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            error=None,
            data={'id': 1, 'name': 'Test Genre', 'created_at': '2023-01-01'}
        )
        
        with patch.object(Genre, '_get_client', return_value=client):
            result = Genre._fetch_by_field('name', 'Test Genre')
            
            assert result is not None
            assert result.name == 'Test Genre'
            table.select.assert_called_once_with('*')
    
    def test_exists_by_field(self, mock_client):
        """Test _exists_by_field method."""
        client, table = mock_client
        
        # Mock existing record
        table.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[{'id': 1}]
        )
        
        with patch.object(Video, '_get_client', return_value=client):
            result = Video._exists_by_field('youtube_id', 'abc123')
            
            assert result is True
            table.select.assert_called_once_with('id')
    
    def test_fetch_all(self, mock_client):
        """Test _fetch_all method."""
        client, table = mock_client
        
        # Mock multiple records
        table.select.return_value.execute.return_value = Mock(
            error=None,
            data=[
                {'id': 1, 'name': 'Genre1', 'created_at': '2023-01-01'},
                {'id': 2, 'name': 'Genre2', 'created_at': '2023-01-02'}
            ]
        )
        
        with patch.object(Genre, '_get_client', return_value=client):
            result = Genre._fetch_all()
            
            assert len(result) == 2
            assert result[0].name == 'Genre1'
            assert result[1].name == 'Genre2'


class TestNewModelAPIs:
    """Test the new simplified model APIs."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock Supabase client."""
        client = Mock()
        table = Mock()
        client.table.return_value = table
        return client, table
    
    def test_video_insert_new_api(self, mock_client):
        """Test Video.insert with new simplified API."""
        client, table = mock_client
        
        # Mock successful insert
        table.insert.return_value.execute.return_value = Mock(
            error=None,
            data=[{
                'id': 1, 'title': 'Test Video', 'youtube_id': 'abc123',
                'is_premium': False, 'transcript': 'test', 'language': 'en'
            }]
        )
        
        with patch.object(Video, '_get_client', return_value=client):
            result = Video.insert('Test Video', 'abc123', False, 'test transcript')
            
            assert result is not None
            assert result.title == 'Test Video'
            assert result.youtube_id == 'abc123'
    
    def test_genre_insert_new_api(self, mock_client):
        """Test Genre.insert with new simplified API."""
        client, table = mock_client
        
        # Mock successful insert
        table.insert.return_value.execute.return_value = Mock(
            error=None,
            data=[{'id': 1, 'name': 'Action', 'created_at': '2023-01-01'}]
        )
        
        with patch.object(Genre, '_get_client', return_value=client):
            result = Genre.insert('Action')
            
            assert result is not None
            assert result.name == 'Action'
    
    def test_new_getter_methods(self, mock_client):
        """Test new getter methods like get_by_youtube_id."""
        client, table = mock_client
        
        # Mock successful fetch
        table.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            error=None,
            data={
                'id': 1, 'title': 'Test Video', 'youtube_id': 'abc123',
                'is_premium': False, 'transcript': 'test', 'language': 'en'
            }
        )
        
        with patch.object(Video, '_get_client', return_value=client):
            result = Video.get_by_youtube_id('abc123')
            
            assert result is not None
            assert result.youtube_id == 'abc123'


class TestDatabaseRefactoringSuccess:
    """Test that the database refactoring was successful (TODO #4 - COMPLETED)."""
    
    def test_redundant_code_eliminated(self):
        """Test that redundant database code has been eliminated."""
        # All models should now use BaseSupabaseModel methods
        models = [Video, Genre, Series, SeriesGenre]
        
        for model in models:
            # Should inherit from BaseSupabaseModel
            assert issubclass(model, BaseSupabaseModel)
            
            # Should have access to common methods
            assert hasattr(model, '_insert_with_duplicate_handling')
            assert hasattr(model, '_fetch_by_field')
            assert hasattr(model, '_exists_by_field')
    
    def test_duplicate_handling_unified(self):
        """Test that duplicate handling is now unified."""
        # All models should use the same duplicate handling logic
        models = [Video, Genre, Series, SeriesGenre]
        
        for model in models:
            # Should have the unified insert method logic through base class
            assert hasattr(model, '_insert_with_duplicate_handling')
            
            # The base method should be the same across all models
            base_method = BaseSupabaseModel._insert_with_duplicate_handling
            model_method = getattr(model, '_insert_with_duplicate_handling')
            assert model_method is base_method
    
    def test_fetch_operations_unified(self):
        """Test that fetch operations are now unified."""
        models = [Video, Genre, Series, SeriesGenre]
        
        for model in models:
            # Should have unified fetch methods
            assert hasattr(model, '_fetch_by_field')
            assert hasattr(model, '_fetch_all')
            assert hasattr(model, '_exists_by_field')
    
    def test_error_handling_unified(self):
        """Test that error handling is now unified."""
        # All models should use the same error handling logic in BaseSupabaseModel
        models = [Video, Genre, Series, SeriesGenre]
        
        for model in models:
            # Error handling should be in the base class methods
            import inspect
            
            # Check that base methods have proper error handling
            insert_source = inspect.getsource(BaseSupabaseModel._insert_with_duplicate_handling)
            assert 'try:' in insert_source
            assert 'except Exception' in insert_source
            assert 'logger.error' in insert_source
    
    def test_client_access_unified(self):
        """Test that client access is now unified."""
        models = [Video, Genre, Series, SeriesGenre]
        
        for model in models:
            # All should use the same client access method
            assert hasattr(model, '_get_client')
            
            # Should use the global get_supabase_client function
            client_method = getattr(model, '_get_client')
            assert client_method is BaseSupabaseModel._get_client
    
    def test_api_consistency(self):
        """Test that the API is now consistent across models."""
        # All models should have similar method signatures and behavior
        models = [Video, Genre, Series, SeriesGenre]
        
        for model in models:
            # Should implement required abstract methods
            assert hasattr(model, 'get_table_name')
            assert hasattr(model, 'from_row')
            assert hasattr(model, 'to_dict')
            
            # Should have insert method
            assert hasattr(model, 'insert')
            assert callable(getattr(model, 'insert'))
    
    def test_code_reduction(self):
        """Test that code duplication has been significantly reduced."""
        # The individual model classes should now be much smaller
        import inspect
        
        # Check Video class size (should be much smaller now)
        video_source = inspect.getsource(Video)
        video_lines = len(video_source.strip().split('\n'))
        
        # Should be significantly smaller than original (which had ~100+ lines)
        assert video_lines < 60, f"Video class still too large: {video_lines} lines"
        
        # Check Genre class size
        genre_source = inspect.getsource(Genre)
        genre_lines = len(genre_source.strip().split('\n'))
        
        # Genre should also be much smaller
        assert genre_lines < 40, f"Genre class still too large: {genre_lines} lines"