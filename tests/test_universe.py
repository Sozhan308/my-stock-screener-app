from minervini_scanner.universe import parse_equity_list

SAMPLE = """SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER
TCS,Tata Consultancy Services Limited,EQ,25-AUG-2004,1,1,INE467B01029
21STCENMGM,21st Century Management Services Limited,BE,03-MAY-1995,10,1,INE253B01015
M&M,Mahindra & Mahindra Limited,EQ,01-JAN-1996,5,1,INE101A01026
TCS,Duplicate row,EQ,25-AUG-2004,1,1,INE467B01029
"""


def test_parse_equity_list_keeps_only_regular_series_sorted_and_unique():
    assert parse_equity_list(SAMPLE) == ["M&M", "TCS"]
