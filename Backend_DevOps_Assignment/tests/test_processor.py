from app import processor


def test_parse_date():
    assert processor.parse_date('04-09-2024') == '2024-09-04'
    assert processor.parse_date('2024/02/05') == '2024-02-05'


def test_parse_amount():
    assert processor.parse_amount('$1,234.56') == 1234.56
    assert processor.parse_amount('987.5') == 987.5


def test_llm_batch():
    recs = [{'merchant': 'Swiggy'}, {'merchant': 'Amazon'}, {'merchant': 'Ola'}]
    cats = processor.call_llm_batch(recs)
    assert cats[0] == 'Food'
    assert cats[1] == 'Shopping'
    assert cats[2] == 'Transport'
