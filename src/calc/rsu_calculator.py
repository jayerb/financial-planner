from typing import Dict, List


class RSUCalculator:
    """Calculator for Restricted Stock Unit (RSU) vesting values.

    Computes the value of vested RSU grants for a given year, accounting for:
    - Previous grants that are still vesting
    - New annual grants that increase yearly
    - Stock price appreciation over time
    """

    def __init__(self, 
                 previous_grants: List[Dict] = [],
                 first_year: int = 2026,
                 last_year: int = 2030,
                 first_year_stock_price: float = 100.00, 
                 first_year_grant_value: float = 10000.0,
                 annual_grant_increase: float = 0.05,
                 expected_share_price_growth_fraction: float = 0.07,
                 ):
        """Initialize with stock price parameters.

        Args:
        
            previous_grants: List of previous RSU grants with their details.
            first_year: The first year of the financial program.
            last_year: The final year of the financial program.
            first_year_stock_price: The price per share at the start of the financial program (not the start of the grant)
            expected_share_price_growth_fraction: Annual growth rate for stock price (e.g., 0.07 for 7%).
        """
        self.vesting_schedule = {}
        self.vested_value = {}
        grants = previous_grants
        stock_prices = {}
        for year in range(first_year, last_year + 1):
            stock_price = first_year_stock_price * ((1 + expected_share_price_growth_fraction) ** (year - first_year))
            stock_prices[year] = stock_price
            grant_value = first_year_grant_value * ((1 + annual_grant_increase) ** (year - first_year))
            # Only add grants if both grant_value and stock_price are positive
            if grant_value > 0 and stock_price > 0:
                grants.append({'year': year,
                               'grantShares': grant_value / stock_price,
                               'vestingPeriodYears': 4})

        """ collect vesting amounts for each year in the program """
        for grant in grants:
            grant_year = grant.get('year')
            grant_shares = grant.get('grantShares', 0)
            vesting_period = grant.get('vestingPeriodYears', 4)
            # collect the vesting schedule from the previous grants
            for year in range(grant_year + 1, grant_year + vesting_period + 1):
                if year <= last_year:
                    if year not in self.vesting_schedule:
                        self.vesting_schedule[year] = 0
                    self.vesting_schedule[year] += grant_shares / vesting_period
        # now, start calculating the vesting schedule for future grants
        for year in range(first_year, last_year + 1):
            self.vested_value[year] = self.vesting_schedule.get(year, 0) * stock_prices[year]
    

