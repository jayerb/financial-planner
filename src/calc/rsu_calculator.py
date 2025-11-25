from typing import Dict, List


class RSUCalculator:
    """Calculator for Restricted Stock Unit (RSU) vesting values.

    Computes the value of vested RSU grants for a given year, accounting for:
    - Previous grants that are still vesting
    - New annual grants that increase yearly
    - Stock price appreciation over time
    """

    def __init__(self, current_stock_price: float, expected_share_price_growth_fraction: float):
        """Initialize with stock price parameters.

        Args:
            current_stock_price: The current price per share.
            expected_share_price_growth_fraction: Annual growth rate for stock price (e.g., 0.07 for 7%).
        """
        self.current_stock_price = current_stock_price
        self.expected_share_price_growth_fraction = expected_share_price_growth_fraction

    def stock_price_for_year(self, base_year: int, target_year: int) -> float:
        """Calculate the projected stock price for a target year.

        Args:
            base_year: The year when current_stock_price applies.
            target_year: The year for which to calculate the price.

        Returns:
            The projected stock price.
        """
        years_elapsed = target_year - base_year
        return self.current_stock_price * ((1 + self.expected_share_price_growth_fraction) ** years_elapsed)

    def vested_shares_from_grant(self, grant_year: int, grant_shares: int,
                                  vesting_period_years: int, target_year: int) -> float:
        """Calculate shares vesting in target_year from a single grant.

        Assumes equal vesting over the vesting period (e.g., 25% per year for 4-year vest).

        Args:
            grant_year: The year the grant was awarded.
            grant_shares: Total number of shares in the grant.
            vesting_period_years: Number of years over which shares vest.
            target_year: The year to calculate vesting for.

        Returns:
            Number of shares vesting in target_year (0 if outside vesting window).
        """
        # Vesting starts the year after grant (first vest at grant_year + 1)
        first_vest_year = grant_year + 1
        last_vest_year = grant_year + vesting_period_years

        if target_year < first_vest_year or target_year > last_vest_year:
            return 0

        shares_per_year = grant_shares / vesting_period_years
        return shares_per_year

    def calculate_vested_value(self, spec: dict, target_year: int) -> Dict:
        """Calculate total vested RSU value for a specific year.

        Args:
            spec: The specification dictionary containing RSU details.
            target_year: The year for which to calculate vested value.

        Returns:
            Dictionary with vesting details including:
            - vested_shares: Total shares vesting in target_year
            - stock_price: Projected stock price for target_year
            - vested_value: Total dollar value of vested shares
            - vesting_breakdown: List of individual grant contributions
        """
        rsu_config = spec.get('restrictedStockUnits', {})
        first_year = spec.get('firstYear', target_year)

        previous_grants = rsu_config.get('previousGrants', [])
        initial_grant_value = rsu_config.get('initialAnnualGrantValue', 0)
        annual_grant_increase = rsu_config.get('annualGrantIncreaseFraction', 0)
        default_vesting_period = rsu_config.get('vestingPeriodYears', 4)

        # Calculate stock price for target year (base year is the spec's first year)
        stock_price = self.stock_price_for_year(first_year, target_year)

        vesting_breakdown = []
        total_vested_shares = 0

        # Process previous grants (shares are already specified)
        for grant in previous_grants:
            grant_year = grant.get('year')
            grant_shares = grant.get('grantShares', 0)
            vesting_period = grant.get('vestingPeriodYears', default_vesting_period)

            vested = self.vested_shares_from_grant(grant_year, grant_shares,
                                                    vesting_period, target_year)
            if vested > 0:
                total_vested_shares += vested
                vesting_breakdown.append({
                    'grant_year': grant_year,
                    'grant_type': 'previous',
                    'shares_vesting': vested,
                    'value': vested * stock_price
                })

        # Process future grants (from first_year onwards)
        # Calculate how many shares each future grant will have based on grant value and stock price at grant time
        for grant_year in range(first_year, target_year + default_vesting_period):
            years_from_start = grant_year - first_year
            grant_value = initial_grant_value * ((1 + annual_grant_increase) ** years_from_start)

            # Stock price at grant time determines number of shares
            stock_price_at_grant = self.stock_price_for_year(first_year, grant_year)
            grant_shares = grant_value / stock_price_at_grant

            vested = self.vested_shares_from_grant(grant_year, grant_shares,
                                                    default_vesting_period, target_year)
            if vested > 0:
                total_vested_shares += vested
                vesting_breakdown.append({
                    'grant_year': grant_year,
                    'grant_type': 'annual',
                    'grant_value': grant_value,
                    'shares_in_grant': grant_shares,
                    'shares_vesting': vested,
                    'value': vested * stock_price
                })

        total_vested_value = total_vested_shares * stock_price

        return {
            'target_year': target_year,
            'vested_shares': total_vested_shares,
            'stock_price': stock_price,
            'vested_value': total_vested_value,
            'vesting_breakdown': vesting_breakdown
        }

    def calculate_vesting_schedule(self, spec: dict, start_year: int, end_year: int) -> List[Dict]:
        """Calculate vested values for a range of years.

        Args:
            spec: The specification dictionary containing RSU details.
            start_year: First year to calculate.
            end_year: Last year to calculate (inclusive).

        Returns:
            List of vesting results for each year.
        """
        return [self.calculate_vested_value(spec, year) for year in range(start_year, end_year + 1)]
