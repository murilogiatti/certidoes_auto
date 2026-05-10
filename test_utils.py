import unittest
from certidoes import _formatar_data

class TestUtils(unittest.TestCase):
    def test_formatar_data_valid_8_digits(self):
        """Should format 8 digits string to DD/MM/YYYY."""
        self.assertEqual(_formatar_data("28111988"), "28/11/1988")
        self.assertEqual(_formatar_data("01012000"), "01/01/2000")

    def test_formatar_data_with_separators(self):
        """Should handle strings that already have separators by removing them and re-applying if length is 8."""
        self.assertEqual(_formatar_data("28/11/1988"), "28/11/1988")
        self.assertEqual(_formatar_data("28-11-1988"), "28/11/1988")
        self.assertEqual(_formatar_data("28.11.1988"), "28/11/1988")

    def test_formatar_data_with_whitespace(self):
        """Should strip whitespace."""
        self.assertEqual(_formatar_data(" 28111988 "), "28/11/1988")
        self.assertEqual(_formatar_data("\t28111988\n"), "28/11/1988")

    def test_formatar_data_invalid_length(self):
        """Should return cleaned string if length is not 8."""
        # Note: The function returns 'raw' which has been cleaned of /, -, . and stripped
        self.assertEqual(_formatar_data("281188"), "281188")
        self.assertEqual(_formatar_data("1234567"), "1234567")
        self.assertEqual(_formatar_data("123456789"), "123456789")

    def test_formatar_data_non_digits(self):
        """Should return cleaned string if it contains non-digits after cleaning separators."""
        self.assertEqual(_formatar_data("2811198a"), "2811198a")
        self.assertEqual(_formatar_data("abcdefgh"), "abcdefgh")

    def test_formatar_data_empty(self):
        """Should handle empty string."""
        self.assertEqual(_formatar_data(""), "")
        self.assertEqual(_formatar_data("   "), "")

if __name__ == "__main__":
    unittest.main()
