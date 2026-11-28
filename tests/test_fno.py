from minervini_scanner.fno import parse_lot_sizes

SAMPLE = """UNDERLYING                          ,SYMBOL    ,DEC-26     ,JAN-27     
NIFTY 50                            ,NIFTY     ,65         ,65         
Derivatives on Individual Securities,Symbol    ,DEC-26     ,JAN-27     
SAMVRDHNA MTHRSN INTL LTD           ,MOTHERSON ,6150       ,6150       
MAHINDRA & MAHINDRA LTD             ,M&M       ,           ,200        
"""


def test_parse_lot_sizes_keeps_stocks_and_uses_nearest_available_expiry():
    assert parse_lot_sizes(SAMPLE) == {"MOTHERSON": 6150, "M&M": 200}
