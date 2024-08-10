# regex_patterns.py
flipkart_patterns = [
    r'https?://www\.flipkart\.com/.+',
    r'https?://flipkart\.com/.+',
    r'https?://m\.flipkart\.com/.+',
    r'https?://dl\.flipkart\.com/.+',
    r'https?://flipkart\.in/.+',
    r'https?://www\.flipkart\.in/.+',
    r'https?://dl\.flipkart\.in/.+',
    r'https?://m\.flipkart\.in/.+',
    r'https?://fkrt\.cc/.+',
    r'https?://fkrt\.co/.+',
    r'https?://fkrt\.it/.+',
]

amazon_patterns = [
    r'https://www\.amazon\.com/.*',
    r'https://amazon\.com/.*',
    r'https://www\.amazon\.in/.*',
    r'https://amazon\.in/.*',
    r'https://amzn\.in/.*',
    r'https://amzn\.to/.*',
    r'https://amzn\.in/.+',
]


all_url_patterns = amazon_patterns + flipkart_patterns
