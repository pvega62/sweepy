from engine.salary import annual_max_amount, extract_pay


def test_extract_annual_range_with_symbols_and_unit():
    pay = extract_pay("Compensation: $85,000 - $110,000 per year.")
    assert pay == {"min_amount": 85000.0, "max_amount": 110000.0, "currency": "USD", "period": "year"}


def test_extract_range_with_en_dash():
    pay = extract_pay("Salary range: $85,000 – $110,000.")
    assert pay["min_amount"] == 85000.0
    assert pay["max_amount"] == 110000.0


def test_extract_range_with_to_separator_and_trailing_code():
    pay = extract_pay("Salary of 85000 to 110000 USD")
    assert pay["min_amount"] == 85000.0
    assert pay["max_amount"] == 110000.0
    assert pay["currency"] == "USD"


def test_extract_k_suffix_without_symbol():
    pay = extract_pay("Salary: $85k-$110k")
    assert pay["min_amount"] == 85000.0
    assert pay["max_amount"] == 110000.0


def test_extract_leading_currency_code():
    pay = extract_pay("Pay range: EUR 70,000 – 90,000")
    assert pay["min_amount"] == 70000.0
    assert pay["max_amount"] == 90000.0
    assert pay["currency"] == "EUR"


def test_extract_pound_range():
    pay = extract_pay("£65,000 to £75,000 a year")
    assert pay["currency"] == "GBP"
    assert pay["period"] == "year"


def test_extract_hourly_rate_keeps_hour_period():
    pay = extract_pay("Hourly rate: $45 - $55 per hour")
    assert pay["min_amount"] == 45.0
    assert pay["max_amount"] == 55.0
    assert pay["period"] == "hour"


def test_extract_hourly_rate_with_slash_unit():
    pay = extract_pay("Pay is $30/hour.")
    assert pay["period"] == "hour"
    assert pay["max_amount"] == 30.0


def test_extract_monthly_rate():
    pay = extract_pay("This role pays $8,000 - $10,000 per month.")
    assert pay["period"] == "month"
    assert pay["min_amount"] == 8000.0


def test_extract_single_figure_collapses_bounds():
    pay = extract_pay("The base salary for this role is $95,000.")
    assert pay["min_amount"] == 95000.0
    assert pay["max_amount"] == 95000.0


def test_extract_rejects_signing_bonus():
    assert extract_pay("Signing bonus: $10,000. Equity: $50,000.") is None


def test_extract_rejects_funding_round():
    assert extract_pay("We raised $50,000,000 in funding.") is None


def test_extract_rejects_bonus_range():
    assert extract_pay("$10,000 - $20,000 sign-on bonus") is None


def test_extract_prefers_base_salary_over_bonus_in_same_text():
    pay = extract_pay("Salary: $90,000 - $110,000. Signing bonus: $10,000.")
    assert pay["min_amount"] == 90000.0
    assert pay["max_amount"] == 110000.0


def test_extract_keeps_range_when_equity_reads_as_extra():
    pay = extract_pay("Base pay: $120,000 - $150,000 plus equity.")
    assert pay["min_amount"] == 120000.0


def test_extract_ignores_unrelated_numbers():
    assert extract_pay("We have 10k-15k users and 5-7 years of history.") is None


def test_extract_ignores_text_without_pay():
    assert extract_pay("Write API docs and partner with engineering.") is None


def test_extract_ignores_empty_text():
    assert extract_pay("") is None


def test_annual_max_amount_converts_hourly():
    assert annual_max_amount(55, "hour") == 114400.0


def test_annual_max_amount_converts_monthly():
    assert annual_max_amount(8000, "month") == 96000.0


def test_annual_max_amount_defaults_to_year():
    assert annual_max_amount(110000) == 110000.0
    assert annual_max_amount(110000, "unknown") == 110000.0
