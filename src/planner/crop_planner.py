import re
import logging
from typing import Dict, List, Optional

from src.rag.knowledge_base import StardewRAGSystem # Assuming relative import works after setup

logger = logging.getLogger(__name__)

class CropPlanner:
    """
    Handles planning for crop farming in Stardew Valley.
    """
    def __init__(self, rag_system: StardewRAGSystem):
        self.rag_system = rag_system

    def plan_crop_farming(self, crop_name: str, target_yield: int, season: str) -> str:
        """
        Plans a crop farming strategy based on the given parameters.
        """
        try:
            # 1. Retrieve crop information
            crop_info_query = f"{crop_name} Stardew Valley crop growth yield seed price season"
            crop_search_results = self.rag_system.search(crop_info_query, n_results=3)

            logger.info(f"Crop search results for {crop_name}: {crop_search_results}") # TEMP DEBUG

            crop_details = {}
            for result in crop_search_results:
                if crop_name.lower() in result['metadata'].get('title', '').lower():
                    infobox = result['metadata'].get('infobox', {})
                    if infobox:
                        # Prioritize infobox for standard fields
                        crop_details['growth_info'] = self._parse_growth_time(infobox.get('Growth', ''))
                        crop_details['seasons'] = [s.strip().lower() for s in infobox.get('Seasons', '').split(',')]

                        # Improved seed price parsing from infobox
                        seed_price_str = infobox.get('Seed Price')
                        if not seed_price_str:
                            # Check for purchase prices within infobox, e.g., 'Pierre\'s: 60g'
                            for key in infobox:
                                if 'price' in key.lower() or 'cost' in key.lower() or 'g.store' in key.lower(): # 'g.store' for General Store
                                    seed_price_str = infobox.get(key)
                                    if seed_price_str: break
                        if seed_price_str: crop_details['seed_price'] = self._parse_price(seed_price_str)

                        # Yield is often not in 'Harvest' for recurring crops, handle below

                    # Fallback to content parsing if infobox is insufficient or for specific patterns
                    # Improved Yield parsing (more robust for text descriptions)
                    if not crop_details.get('yield'): # Only try to parse if not already found
                        yield_match = re.search(r'yields (\d+-\d+|\d+)', result['content'], re.IGNORECASE)
                        if yield_match:
                            crop_details['yield'] = self._parse_yield(yield_match.group(1))
                        elif 'keeps producing after that' in result['content'].lower() or \
                             'regrowth' in result['content'].lower():
                            # For recurring crops like grapes, assume a yield of 1 per harvest if not specified
                            crop_details['yield'] = {'min': 1, 'max': 1} 
                        else: 
                            # Try to find common yield phrases like 'produces X' or 'gives X'
                            yield_phrases = [r'produces (\d+-\d+|\d+)', r'gives (\d+-\d+|\d+)']
                            for phrase in yield_phrases:
                                phrase_match = re.search(phrase, result['content'], re.IGNORECASE)
                                if phrase_match:
                                    crop_details['yield'] = self._parse_yield(phrase_match.group(1))
                                    break

                    # Improved Seed Price parsing from content (fallback if not found in infobox)
                    if not crop_details.get('seed_price'): # Only try to parse if not already found
                        seed_price_patterns = [
                            r'pierre\'s general store:\s*data-sort-value=\"\d+\">?(\d+)g',
                            r'general store:\s*data-sort-value=\"\d+\">?(\d+)g',
                            r'jojamart:\s*data-sort-value=\"\d+\">?(\d+)g',
                            r'traveling cart:\s*data-sort-value=\"\d+\">?(\d+)g',
                            r'night market\s*\(winter 17\):\s*data-sort-value=\"\d+\">?(\d+)g',
                            r'seeds cost (\d+)g'
                        ]
                        for pattern in seed_price_patterns:
                            seed_price_match = re.search(pattern, result['content'], re.IGNORECASE)
                            if seed_price_match:
                                crop_details['seed_price'] = self._parse_price(seed_price_match.group(1) + 'g') # Add 'g' for parse_price
                                break

                    # Improved Growth Time parsing from content (fallback if not found in infobox)
                    if not crop_details.get('growth_info'):
                         initial_growth_match = re.search(r'growth time:\s*(\d+)\s*days', result['content'], re.IGNORECASE)
                         regrowth_match = re.search(r'regrowth:\s*(\d+)\s*days', result['content'], re.IGNORECASE)

                         if initial_growth_match:
                             initial_growth = int(initial_growth_match.group(1))
                             regrowth = int(regrowth_match.group(1)) if regrowth_match else None
                             crop_details['growth_info'] = {'initial': initial_growth, 'regrowth': regrowth}

                    # Fallback for seasons if not found in infobox
                    if not crop_details.get('seasons'):
                         if "season" in result['content'].lower():
                             match = re.search(r'season[s]?: (.+)', result['content'], re.IGNORECASE)
                             if match:
                                 crop_details['seasons'] = [s.strip().lower() for s in match.group(1).split(',')]

                    if crop_details and crop_details.get('yield') and crop_details.get('growth_info') and crop_details.get('seed_price'):
                        break
            
            logger.info(f"Parsed crop details for {crop_name}: {crop_details}") # TEMP DEBUG

            if not crop_details or not crop_details.get('yield') or not crop_details.get('growth_info') or not crop_details.get('seed_price'):
                return f"Could not find sufficient detailed information for {crop_name}. Please ensure the wiki data contains yield, growth time, and seed price."

            if season.lower() not in crop_details.get('seasons', []):
                 return f"{crop_name} does not grow in {season}. It grows in: {', '.join(crop_details.get('seasons', ['N/A']))}."

            # 2. Calculate planting requirements
            min_yield_per_plant = crop_details['yield']['min']
            max_yield_per_plant = crop_details['yield']['max']
            initial_growth_time = crop_details['growth_info']['initial']
            regrowth_time = crop_details['growth_info']['regrowth']
            min_seed_price = crop_details['seed_price']['min']
            max_seed_price = crop_details['seed_price']['max']

            # Stardew Valley seasons are 28 days
            season_length = 28
            
            # Calculate harvests per season
            harvests_per_season = 0
            if initial_growth_time > 0:
                # First harvest
                harvests_per_season = 1
                remaining_days = season_length - initial_growth_time
                if regrowth_time and regrowth_time > 0:
                    harvests_per_season += remaining_days // regrowth_time
            
            if harvests_per_season == 0:
                return f"Cannot plan for {crop_name} in {season} as it does not seem to grow within the season length ({season_length} days) or has no growth information."

            # Calculate total yield per plant per season (average)
            avg_yield_per_plant_per_harvest = (min_yield_per_plant + max_yield_per_plant) // 2
            total_yield_per_plant_per_season = avg_yield_per_plant_per_harvest * harvests_per_season

            if total_yield_per_plant_per_season == 0:
                return f"Could not calculate a positive yield per plant per season for {crop_name}. Please check the data."


            num_plants = (target_yield + total_yield_per_plant_per_season - 1) // total_yield_per_plant_per_season # Round up

            land_size = num_plants # 1 tile per plant
            total_seed_cost_min = num_plants * min_seed_price
            total_seed_cost_max = num_plants * max_seed_price

            # Basic fertilizer consideration (no longer hardcoded)
            selected_fertilizer = None
            fertilizer_cost_per_plant = 0
            total_fertilizer_cost = 0

            # Estimate total startup funds
            total_startup_funds_min = total_seed_cost_min
            total_startup_funds_max = total_seed_cost_max

            # 3. Format and return plan
            plan = f"## Farming Plan for {target_yield} {crop_name} in {season.capitalize()} ##\n\n"
            plan += f"- **Target Yield**: {target_yield} {crop_name}\n"
            plan += f"- **Estimated Plants Needed**: Approximately {num_plants} plants to achieve your target yield (assuming average yield).\n"
            plan += f"- **Land Size**: You'll need at least {land_size} individual tiles for planting.\n"
            
            seed_cost_str = f"{total_seed_cost_min}g"
            if min_seed_price != max_seed_price:
                seed_cost_str = f"{total_seed_cost_min}g - {total_seed_cost_max}g"
            plan += f"- **Seeds Cost**: Approximately {seed_cost_str}.\n"
            
            startup_funds_str = f"{total_startup_funds_min}g"
            if min_seed_price != max_seed_price:
                startup_funds_str = f"{total_startup_funds_min}g - {total_startup_funds_max}g"
            plan += f"- **Estimated Startup Funds (Seeds + Fertilizer)**: Approximately {startup_funds_str}.\n"
            
            plan += f"- **Growth Information**:\n"
            plan += f"  - Initial Growth Time: {initial_growth_time} days\n"
            if regrowth_time is not None:
                plan += f"  - Regrowth Time: {regrowth_time} days\n"
                plan += f"  - Estimated Harvests per Season: {harvests_per_season} harvests (due to regrowth).\n"
            else:
                plan += f"  - Total Growth Time: {initial_growth_time} days (single harvest).\n"

            plan += "\n**Note**: This plan assumes average yields. Fertilizer is not included as it is optional."
            
            return plan

        except ValueError:
            return "Invalid target yield. Please provide a valid number."
        except Exception as e:
            logger.error(f"Error in CropPlanner.plan_crop_farming: {e}")
            return f"An error occurred while planning your crop: {str(e)}"

    def _parse_yield(self, yield_str: str) -> Dict[str, Optional[int]]:
        """
        Parses yield string (e.g., '1-2', '1', '1-2 per harvest') to a dictionary of min/max yield.
        Returns {'min': int, 'max': int} or {'min': int, 'max': None} if single value.
        """
        yield_str = yield_str.lower().replace('per harvest', '').strip()
        match = re.search(r'(\d+)-?(\d*)', yield_str)
        if match:
            min_yield = int(match.group(1))
            max_yield = int(match.group(2)) if match.group(2) else min_yield
            return {'min': min_yield, 'max': max_yield}
        return {'min': 1, 'max': 1} # Default to 1 if parsing fails or invalid

    def _parse_growth_time(self, growth_time_str: str) -> Dict[str, Optional[int]]:
        """
        Parses growth time string (e.g., '6 Days', '6-8 Days', '6 days, then 2 days regrowth')
        Returns {'initial': int, 'regrowth': int} or {'initial': int, 'regrowth': None}.
        """
        growth_time_str = growth_time_str.lower()
        initial_match = re.search(r'(\d+)\s*days?', growth_time_str)
        regrowth_match = re.search(r'then (\d+)\s*days? regrowth', growth_time_str)

        initial_growth = int(initial_match.group(1)) if initial_match else 0
        regrowth_time = int(regrowth_match.group(1)) if regrowth_match else None
        
        return {'initial': initial_growth, 'regrowth': regrowth_time}

    def _parse_price(self, price_str: str) -> Dict[str, Optional[int]]:
        """
        Parses price string (e.g., '100g', '50-100g', 'Free') to a dictionary of min/max price.
        Returns {'min': int, 'max': int} or {'min': int, 'max': None} if single value.
        """
        price_str_lower = price_str.lower()
        if 'free' in price_str_lower or 'not sold' in price_str_lower or 'n/a' in price_str_lower:
            return {'min': 0, 'max': 0}

        # Try to extract from data-sort-value first
        data_sort_match = re.search(r'data-sort-value="(\d+)"', price_str_lower)
        if data_sort_match:
            price = int(data_sort_match.group(1))
            return {'min': price, 'max': price}

        # Fallback to general price extraction if data-sort-value not found
        # Clean the string for general numeric parsing
        cleaned_price_str = price_str_lower.replace('g', '').replace(',', '').strip()
        # Remove anything in parentheses as it's usually extra info
        cleaned_price_str = re.sub(r'\(.*\)', '', cleaned_price_str).strip()
        
        # Look for a price range (e.g., "100-1000", "100–1000") or single price
        match = re.search(r'(\d+)\s*[-–]?\s*(\d*)', cleaned_price_str) # handles both '-' and '–'
        if match:
            min_price = int(match.group(1))
            max_price = int(match.group(2)) if match.group(2) else min_price
            return {'min': min_price, 'max': max_price}
        
        return {'min': 0, 'max': 0} # Default to 0 if parsing fails or invalid 