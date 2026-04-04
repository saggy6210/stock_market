"""
Pydantic Data Models.
Defines the core data structures used throughout the application.
"""

# TODO: Implement the following Pydantic models:
# - StockSnapshot: symbol, company_name, segment, price, fifty_two_week_low, 
#   near_wkl_pct, pe_ratio
# - AnalysisResult: extends StockSnapshot + business_summary, valuation_view, 
#   profitability_view, shareholding_view, key_points[], risks[], raw_text
# - PipelineRunResult: scanned_count, near_low_stocks[], analyses[], 
#   gemini_failed, gemini_failure_reason


class StockSnapshot:
    """Represents a stock's current market snapshot."""
    
    def __init__(
        self,
        symbol: str = "",
        company_name: str = "",
        segment: str = "",
        price: float = 0.0,
        fifty_two_week_low: float = 0.0,
        near_wkl_pct: float = 0.0,
        pe_ratio: float | None = None,
    ):
        """
        Initialize a stock snapshot.
        
        Args:
            symbol: Stock symbol
            company_name: Company name
            segment: Market segment (e.g., NIFTY 100)
            price: Current price
            fifty_two_week_low: 52-week low price
            near_wkl_pct: Percentage above 52-week low
            pe_ratio: Price-to-earnings ratio
        """
        self.symbol = symbol
        self.company_name = company_name
        self.segment = segment
        self.price = price
        self.fifty_two_week_low = fifty_two_week_low
        self.near_wkl_pct = near_wkl_pct
        self.pe_ratio = pe_ratio


class AnalysisResult(StockSnapshot):
    """Extends StockSnapshot with AI analysis results."""
    
    def __init__(
        self,
        business_summary: str = "",
        valuation_view: str = "",
        profitability_view: str = "",
        shareholding_view: str = "",
        key_points: list[str] = None,
        risks: list[str] = None,
        raw_text: str = "",
        **kwargs,
    ):
        """
        Initialize an analysis result.
        
        Args:
            business_summary: Summary of the business
            valuation_view: Valuation analysis
            profitability_view: Profitability analysis
            shareholding_view: Shareholding pattern analysis
            key_points: List of key investment points
            risks: List of identified risks
            raw_text: Raw analysis text
            **kwargs: Arguments passed to StockSnapshot
        """
        super().__init__(**kwargs)
        self.business_summary = business_summary
        self.valuation_view = valuation_view
        self.profitability_view = profitability_view
        self.shareholding_view = shareholding_view
        self.key_points = key_points or []
        self.risks = risks or []
        self.raw_text = raw_text


class PipelineRunResult:
    """Result of a pipeline run."""
    
    def __init__(
        self,
        scanned_count: int = 0,
        near_low_stocks: list[StockSnapshot] = None,
        analyses: list[AnalysisResult] = None,
        gemini_failed: bool = False,
        gemini_failure_reason: str = "",
    ):
        """
        Initialize a pipeline run result.
        
        Args:
            scanned_count: Total stocks scanned
            near_low_stocks: Stocks near 52-week low
            analyses: Analysis results
            gemini_failed: Whether Gemini analysis failed
            gemini_failure_reason: Reason for Gemini failure
        """
        self.scanned_count = scanned_count
        self.near_low_stocks = near_low_stocks or []
        self.analyses = analyses or []
        self.gemini_failed = gemini_failed
        self.gemini_failure_reason = gemini_failure_reason
