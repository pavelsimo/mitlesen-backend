"""Tests for dictionary parser refactoring (TODO #6 - Parser complexity reduction)."""
import pytest
from unittest.mock import Mock, patch, mock_open
from mitlesen.dictionary import (
    BaseDictionaryParser, 
    XMLParserMixin, 
    JSONLParserMixin,
    GermanWiktionaryParser,
    JapaneseJMDictParser,
    JapaneseWiktionaryParser,
    DictRow
)


class TestBaseDictionaryParser:
    """Test the base parser class and shared utilities."""
    
    def test_abstract_parser_cannot_be_instantiated(self):
        """Test that BaseDictionaryParser cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseDictionaryParser("/fake/path")
    
    def test_shared_utilities_available(self):
        """Test that shared utility methods are available."""
        required_methods = [
            'make_entry_id',
            'canonicalize_pos',
            'extract_gender_from_tags',
            'extract_gender_from_templates',
            'extract_meanings_from_senses',
            'clean_text_content'
        ]
        
        for method in required_methods:
            assert hasattr(BaseDictionaryParser, method)
            assert callable(getattr(BaseDictionaryParser, method))
    
    def test_make_entry_id_method(self):
        """Test the shared make_entry_id method."""
        # Create a concrete parser to test the method
        class TestParser(BaseDictionaryParser):
            def parse(self):
                pass
        
        parser = TestParser("/fake/path")
        result = parser.make_entry_id("en", "test", "noun")
        assert isinstance(result, str)
        assert result  # Should not be empty
    
    def test_extract_gender_from_tags(self):
        """Test gender extraction from tags."""
        class TestParser(BaseDictionaryParser):
            def parse(self):
                pass
        
        parser = TestParser("/fake/path")
        
        # Test with masculine tag
        tags = ["masculine", "other"]
        result = parser.extract_gender_from_tags(tags)
        assert result == "m"
        
        # Test with feminine tag
        tags = ["feminine"]
        result = parser.extract_gender_from_tags(tags)
        assert result == "f"
        
        # Test with no gender tags
        tags = ["other", "random"]
        result = parser.extract_gender_from_tags(tags)
        assert result is None
    
    def test_clean_text_content(self):
        """Test text cleaning utility."""
        class TestParser(BaseDictionaryParser):
            def parse(self):
                pass
        
        parser = TestParser("/fake/path")
        
        # Test cleaning with various punctuation
        text = "Test (with) punctuation, here"
        result = parser.clean_text_content(text)
        expected = "test with punctuation here"
        assert result == expected
        
        # Test with empty/None text
        assert parser.clean_text_content("") == ""
        assert parser.clean_text_content(None) == ""


class TestXMLParserMixin:
    """Test XML parsing utilities."""
    
    def test_xml_text_extraction_methods(self):
        """Test that XML parsing methods are available."""
        assert hasattr(XMLParserMixin, 'extract_xml_text_list')
        assert hasattr(XMLParserMixin, 'extract_xml_text_single')
        assert callable(XMLParserMixin.extract_xml_text_list)
        assert callable(XMLParserMixin.extract_xml_text_single)


class TestJSONLParserMixin:
    """Test JSONL parsing utilities."""
    
    def test_jsonl_parsing_method(self):
        """Test that JSONL parsing method is available."""
        assert hasattr(JSONLParserMixin, 'parse_jsonl_file')
        assert callable(JSONLParserMixin.parse_jsonl_file)


class TestGermanWiktionaryParserRefactored:
    """Test the refactored German Wiktionary parser."""
    
    def test_inherits_from_base_and_mixins(self):
        """Test that parser inherits from base class and mixins."""
        assert issubclass(GermanWiktionaryParser, BaseDictionaryParser)
        assert issubclass(GermanWiktionaryParser, JSONLParserMixin)
    
    @patch('builtins.open', mock_open(read_data='{"lang": "German", "word": "test", "pos": "noun", "senses": [{"glosses": ["a test"]}]}'))
    def test_parse_uses_base_class_methods(self):
        """Test that parse method uses base class utilities."""
        parser = GermanWiktionaryParser("/fake/path.jsonl")
        
        # Should be able to parse without errors using base class methods
        results = list(parser.parse())
        assert len(results) == 1
        assert isinstance(results[0], DictRow)
        assert results[0].lang == "de"
        assert results[0].word == "test"
    
    def test_extract_gender_method_exists(self):
        """Test that gender extraction method exists."""
        parser = GermanWiktionaryParser("/fake/path.jsonl")
        assert hasattr(parser, '_extract_gender')
        assert callable(parser._extract_gender)
    
    def test_simplified_parse_structure(self):
        """Test that parse method has been simplified."""
        import inspect
        
        source = inspect.getsource(GermanWiktionaryParser.parse)
        
        # Should use base class methods
        assert 'self.canonicalize_pos' in source
        assert 'self.extract_meanings_from_senses' in source
        assert 'self.make_entry_id' in source
        
        # Should use mixin methods
        assert 'self.parse_jsonl_file' in source


class TestJapaneseJMDictParserRefactored:
    """Test the refactored Japanese JMDict parser."""
    
    def test_inherits_from_base_and_mixins(self):
        """Test that parser inherits from base class and mixins."""
        assert issubclass(JapaneseJMDictParser, BaseDictionaryParser)
        assert issubclass(JapaneseJMDictParser, XMLParserMixin)
    
    def test_uses_base_class_utilities(self):
        """Test that methods use base class utilities."""
        parser = JapaneseJMDictParser("/fake/path.xml")
        
        # Test that methods use base class utilities
        assert hasattr(parser, 'clean_text_content')
        assert hasattr(parser, 'canonicalize_pos')
        assert hasattr(parser, 'make_entry_id')
    
    def test_uses_xml_mixin_utilities(self):
        """Test that methods use XML mixin utilities."""
        import inspect
        
        # Check that extract methods use XML mixin utilities
        source = inspect.getsource(JapaneseJMDictParser.extract_pos_and_remarks)
        assert 'self.extract_xml_text_list' in source
        
        source = inspect.getsource(JapaneseJMDictParser.extract_furigana)
        assert 'self.extract_xml_text_list' in source
        
        source = inspect.getsource(JapaneseJMDictParser.extract_meanings)
        assert 'self.extract_xml_text_list' in source
    
    def test_parse_method_simplified(self):
        """Test that parse method uses base class utilities."""
        import inspect
        
        source = inspect.getsource(JapaneseJMDictParser.parse)
        
        # Should use base class methods
        assert 'self.extract_xml_text_single' in source
        assert 'self.make_entry_id' in source
        
        # Should use source_path from base class
        assert 'self.source_path' in source


class TestJapaneseWiktionaryParserRefactored:
    """Test the refactored Japanese Wiktionary parser."""
    
    def test_inherits_from_base_and_mixins(self):
        """Test that parser inherits from base class and mixins."""
        assert issubclass(JapaneseWiktionaryParser, BaseDictionaryParser)
        assert issubclass(JapaneseWiktionaryParser, JSONLParserMixin)
    
    def test_complex_parse_method_simplified(self):
        """Test that the complex parse method has been broken down."""
        parser = JapaneseWiktionaryParser("/fake/path.jsonl")
        
        # Should have helper methods extracted
        helper_methods = [
            '_build_entry_lookup',
            '_is_redirect_entry',
            '_process_redirect_entry',
            '_process_direct_entry',
            '_create_dict_row'
        ]
        
        for method in helper_methods:
            assert hasattr(parser, method)
            assert callable(getattr(parser, method))
    
    def test_duplication_eliminated(self):
        """Test that code duplication has been eliminated."""
        import inspect
        
        # The _create_dict_row method should handle the common DictRow creation
        source = inspect.getsource(JapaneseWiktionaryParser._create_dict_row)
        
        # Should contain the common logic for creating DictRow
        assert 'kana = self.extract_kana' in source
        assert 'romaji = self.extract_romaji' in source
        assert 'furigana_val = self.extract_furigana' in source
        assert 'meanings = self.extract_meanings' in source
        assert 'level = self.extract_level' in source
        assert 'self.make_entry_id' in source
    
    def test_parse_method_structure_improved(self):
        """Test that main parse method has cleaner structure."""
        import inspect
        
        source = inspect.getsource(JapaneseWiktionaryParser.parse)
        
        # Should have clear separation of concerns
        assert '_build_entry_lookup' in source
        assert '_is_redirect_entry' in source
        assert '_process_redirect_entry' in source
        assert '_process_direct_entry' in source
        
        # Should be much shorter and cleaner
        lines = source.split('\n')
        # Main logic should be concise (excluding docstring and helper method calls)
        logic_lines = [line for line in lines if line.strip() and not line.strip().startswith('"""')]
        assert len(logic_lines) < 20  # Should be much shorter than original


class TestParserComplexityReductionSuccess:
    """Test that parser complexity reduction was successful (TODO #6 - COMPLETED)."""
    
    def test_common_parsing_patterns_extracted(self):
        """Test that common parsing patterns have been extracted to base class."""
        # Base class should provide common utilities
        common_utilities = [
            'make_entry_id',
            'canonicalize_pos', 
            'extract_gender_from_tags',
            'extract_gender_from_templates',
            'extract_meanings_from_senses',
            'clean_text_content'
        ]
        
        for utility in common_utilities:
            assert hasattr(BaseDictionaryParser, utility)
    
    def test_xml_json_processing_utilities_created(self):
        """Test that shared XML/JSON processing utilities were created."""
        # XML utilities
        assert hasattr(XMLParserMixin, 'extract_xml_text_list')
        assert hasattr(XMLParserMixin, 'extract_xml_text_single')
        
        # JSONL utilities
        assert hasattr(JSONLParserMixin, 'parse_jsonl_file')
    
    def test_large_methods_broken_down(self):
        """Test that large methods have been broken down into smaller ones."""
        # JapaneseWiktionaryParser should have helper methods
        helper_methods = [
            '_build_entry_lookup',
            '_is_redirect_entry', 
            '_process_redirect_entry',
            '_process_direct_entry',
            '_create_dict_row'
        ]
        
        for method in helper_methods:
            assert hasattr(JapaneseWiktionaryParser, method)
    
    def test_code_reuse_increased(self):
        """Test that code reuse has been increased across parsers."""
        # All parsers should inherit from the same base
        parsers = [GermanWiktionaryParser, JapaneseJMDictParser, JapaneseWiktionaryParser]
        
        for parser_class in parsers:
            assert issubclass(parser_class, BaseDictionaryParser)
            
            # Should have access to common methods
            assert hasattr(parser_class, 'make_entry_id')
            assert hasattr(parser_class, 'canonicalize_pos')
            assert hasattr(parser_class, 'clean_text_content')
    
    def test_parser_files_maintainability_improved(self):
        """Test that overall maintainability has been improved."""
        import inspect
        
        # Base class should be focused on common functionality
        base_methods = inspect.getmembers(BaseDictionaryParser, predicate=inspect.isfunction)
        base_method_names = [name for name, _ in base_methods if not name.startswith('_')]
        
        # Should have reasonable number of utility methods
        assert len(base_method_names) >= 5  # Has utility methods
        assert len(base_method_names) <= 10  # Not overwhelmed
        
        # Mixins should be focused on specific concerns
        xml_methods = inspect.getmembers(XMLParserMixin, predicate=inspect.isfunction)
        jsonl_methods = inspect.getmembers(JSONLParserMixin, predicate=inspect.isfunction)
        
        # Should have focused responsibilities
        assert len(xml_methods) >= 2   # Has XML utilities
        assert len(xml_methods) <= 5   # Focused scope
        assert len(jsonl_methods) >= 1 # Has JSONL utilities  
        assert len(jsonl_methods) <= 3 # Focused scope