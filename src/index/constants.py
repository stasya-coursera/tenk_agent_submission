from typing import Dict, Final
from index.types import ItemInfo, ItemName


ITEMS: Final[Dict[ItemName, ItemInfo]] = {
    "Item 1": ItemInfo(
        item="Item 1",
        technical_name="business",
        display_name="Business",
        description="Overview of the company’s operations, products, services, and strategy"
    ),
    "Item 1A": ItemInfo(
        item="Item 1A",
        technical_name="risk_factors",
        display_name="Risk Factors",
        description="Material risks that could affect the company’s business or financial condition"
    ),
    "Item 1B": ItemInfo(
        item="Item 1B",
        technical_name="unresolved_staff_comments",
        display_name="Unresolved Staff Comments",
        description="Comments from the SEC staff that remain unresolved"
    ),
    "Item 1C": ItemInfo(
        item="Item 1C",
        technical_name="cybersecurity",
        display_name="Cybersecurity",
        description="Company cybersecurity risk management, strategy, and governance"
    ),
    "Item 2": ItemInfo(
        item="Item 2",
        technical_name="properties",
        display_name="Properties",
        description="Description of principal properties owned or leased"
    ),
    "Item 3": ItemInfo(
        item="Item 3",
        technical_name="legal_proceedings",
        display_name="Legal Proceedings",
        description="Material pending legal proceedings"
    ),
    "Item 4": ItemInfo(
        item="Item 4",
        technical_name="mine_safety",
        display_name="Mine Safety Disclosures",
        description="Mine safety information (typically not applicable)"
    ),
    "Item 5": ItemInfo(
        item="Item 5",
        technical_name="market_information",
        display_name="Market for Registrant’s Common Equity",
        description="Market information, dividends, and issuer purchases of equity securities"
    ),
    "Item 6": ItemInfo(
        item="Item 6",
        technical_name="selected_financial_data",
        display_name="Selected Financial Data",
        description="Historical financial highlights (largely deprecated but still present)"
    ),
    "Item 7": ItemInfo(
        item="Item 7",
        technical_name="mdna",
        display_name="Management’s Discussion and Analysis",
        description="Management’s perspective on financial condition and results of operations"
    ),
    "Item 7A": ItemInfo(
        item="Item 7A",
        technical_name="quantitative_market_risk",
        display_name="Quantitative and Qualitative Disclosures About Market Risk",
        description="Exposure to market risk such as interest rates, FX, or commodity prices"
    ),
    "Item 8": ItemInfo(
        item="Item 8",
        technical_name="financial_statements",
        display_name="Financial Statements and Supplementary Data",
        description="Audited financial statements and notes"
    ),
    "Item 9": ItemInfo(
        item="Item 9",
        technical_name="accounting_changes",
        display_name="Changes in and Disagreements with Accountants",
        description="Changes in accountants and accounting disagreements"
    ),
    "Item 9A": ItemInfo(
        item="Item 9A",
        technical_name="controls_and_procedures",
        display_name="Controls and Procedures",
        description="Disclosure controls and internal control over financial reporting"
    ),
    "Item 9B": ItemInfo(
        item="Item 9B",
        technical_name="other_information",
        display_name="Other Information",
        description="Information not required elsewhere"
    ),
    "Item 9C": ItemInfo(
        item="Item 9C",
        technical_name="foreign_jurisdiction_disclosure",
        display_name="Disclosure Regarding Foreign Jurisdictions",
        description="Disclosure related to foreign jurisdiction restrictions (newer item)"
    ),
    "Item 10": ItemInfo(
        item="Item 10",
        technical_name="directors_and_officers",
        display_name="Directors, Executive Officers and Corporate Governance",
        description="Information about directors, officers, and governance"
    ),
    "Item 11": ItemInfo(
        item="Item 11",
        technical_name="executive_compensation",
        display_name="Executive Compensation",
        description="Compensation of executive officers"
    ),
    "Item 12": ItemInfo(
        item="Item 12",
        technical_name="security_ownership",
        display_name="Security Ownership of Certain Beneficial Owners",
        description="Equity ownership by management and major shareholders"
    ),
    "Item 13": ItemInfo(
        item="Item 13",
        technical_name="related_transactions",
        display_name="Certain Relationships and Related Transactions",
        description="Related-party transactions"
    ),
    "Item 15": ItemInfo(
        item="Item 15",
        technical_name="exhibits",
        display_name="Exhibits and Financial Statement Schedules",
        description="List of exhibits and schedules"
    ),
    "Item 16": ItemInfo(
        item="Item 16",
        technical_name="form_10k_summary",
        display_name="Form 10-K Summary",
        description="Optional summary of the Form 10-K"
    ),
}
