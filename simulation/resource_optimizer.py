"""
Smart resource optimization algorithms for Mars greenhouse management.
Based on NASA research and Mars mission planning best practices.
"""
from dataclasses import dataclass
from typing import List, Dict, Tuple
import math


@dataclass
class WateringPlan:
    """Optimal watering plan for plants."""
    plant_name: str
    water_amount_liters: float
    priority: int  # 1=critical, 2=high, 3=normal
    reason: str


@dataclass
class RationPlan:
    """Food rationing plan for astronauts."""
    astronaut_name: str
    calories_allocated: float
    protein_allocated_g: float
    priority_score: float  # Higher = more critical need
    reason: str


def calculate_optimal_watering(plants: list, available_water: float, days_to_next_resupply: int = 30) -> List[WateringPlan]:
    """
    Calculate optimal water distribution based on plant needs and criticality.
    
    Algorithm based on:
    - Plant growth stage (seedlings need less, mature need more)
    - Current hydration level (critical < 20%, low < 50%, normal >= 50%)
    - Days until harvest (prioritize near-harvest plants)
    - Water efficiency (liters per kg yield)
    """
    plans = []
    
    for plant in plants:
        # Base water need: 0.5L per plant count per watering
        base_water = plant['count'] * 0.5
        
        # Calculate priority based on multiple factors
        hydration = plant['hydration']
        days_to_harvest = plant['growth_cycle'] - plant['days_planted']
        
        # Priority scoring (0-100)
        priority_score = 0
        
        # Factor 1: Hydration urgency (0-40 points)
        if hydration < 20:
            priority_score += 40  # Critical - plant dying
            reason = "CRITICAL: Plant wilting"
            priority = 1
        elif hydration < 50:
            priority_score += 25  # High priority
            reason = "Low hydration"
            priority = 2
        elif hydration < 70:
            priority_score += 15  # Medium priority
            reason = "Moderate hydration"
            priority = 2
        else:
            priority_score += 5  # Maintenance
            reason = "Maintenance watering"
            priority = 3
        
        # Factor 2: Harvest proximity (0-30 points)
        if plant['harvestable']:
            priority_score += 30  # Max priority - ready to harvest
            reason = "Ready for harvest - maintain quality"
            priority = min(priority, 1)
        elif days_to_harvest <= 7:
            priority_score += 25  # Near harvest
            reason = f"Near harvest ({days_to_harvest} days)"
            priority = min(priority, 2)
        elif days_to_harvest <= 14:
            priority_score += 15
        
        # Factor 3: Growth stage (0-20 points)
        stage = plant['stage']
        if stage == 'mature':
            priority_score += 20  # Mature plants need consistent water
        elif stage == 'vegetative':
            priority_score += 15  # Active growth
        elif stage == 'seedling':
            priority_score += 10  # Less water needed
        
        # Factor 4: Caloric value (0-10 points) - prioritize high-calorie crops
        calorie_values = {"Potato": 10, "Beans": 8, "Radish": 3, "Lettuce": 2, "Herbs": 1}
        priority_score += calorie_values.get(plant['name'], 5)
        
        # Calculate optimal water amount based on need
        if hydration < 30:
            # Emergency watering - restore to 60%
            water_multiplier = 1.5
        elif hydration < 60:
            # Standard watering - restore to 80%
            water_multiplier = 1.0
        else:
            # Light watering - maintain at 90%
            water_multiplier = 0.5
        
        optimal_water = base_water * water_multiplier
        
        plans.append(WateringPlan(
            plant_name=plant['name'],
            water_amount_liters=optimal_water,
            priority=priority,
            reason=reason
        ))
    
    # Sort by priority (1=highest) then by priority_score
    plans.sort(key=lambda p: (p.priority, -sum(ord(c) for c in p.reason)))
    
    # Adjust for water availability
    total_water_needed = sum(p.water_amount_liters for p in plans)
    if total_water_needed > available_water * 0.8:  # Reserve 20% for crew
        # Scale down water allocation proportionally, but prioritize critical plants
        critical_water = sum(p.water_amount_liters for p in plans if p.priority == 1)
        if critical_water <= available_water * 0.8:
            # Can water all critical plants
            remaining_water = available_water * 0.8 - critical_water
            non_critical_water = sum(p.water_amount_liters for p in plans if p.priority > 1)
            if non_critical_water > 0:
                scale_factor = remaining_water / non_critical_water
                for plan in plans:
                    if plan.priority > 1:
                        plan.water_amount_liters *= scale_factor
        else:
            # Even critical plants need rationing
            scale_factor = (available_water * 0.8) / total_water_needed
            for plan in plans:
                plan.water_amount_liters *= scale_factor
    
    return plans


def calculate_optimal_rationing(astronauts: list, available_food_kcal: float, 
                                emergency_rations_kcal: float, days_until_harvest: int) -> List[RationPlan]:
    """
    Calculate optimal food distribution during shortages.
    
    Algorithm based on:
    - Individual health status (cognitive, immune, micronutrient scores)
    - Calorie deficit accumulation
    - Mission-critical roles (could be extended)
    - Survival probability optimization
    
    Strategy:
    - Normal: Everyone gets 3000 kcal/day
    - Shortage: Prioritize healthiest to maintain mission capability
    - Crisis: Minimum 1500 kcal/day to prevent death, distribute rest by need
    """
    plans = []
    alive_count = sum(1 for a in astronauts if a['alive'])
    
    if alive_count == 0:
        return plans
    
    total_daily_need = alive_count * 3000
    total_available = available_food_kcal + emergency_rations_kcal
    days_of_food = total_available / total_daily_need if total_daily_need > 0 else 0
    
    # Determine rationing mode
    if days_of_food >= days_until_harvest + 10:
        # NORMAL MODE: Plenty of food
        for astronaut in astronauts:
            if not astronaut['alive']:
                continue
            plans.append(RationPlan(
                astronaut_name=astronaut['name'],
                calories_allocated=3000.0,
                protein_allocated_g=112.5,
                priority_score=50.0,
                reason="Normal rations"
            ))
    
    elif days_of_food >= days_until_harvest:
        # CONSERVATION MODE: Tight but manageable
        # Reduce to 2500 kcal/day to extend supplies
        for astronaut in astronauts:
            if not astronaut['alive']:
                continue
            plans.append(RationPlan(
                astronaut_name=astronaut['name'],
                calories_allocated=2500.0,
                protein_allocated_g=93.75,
                priority_score=60.0,
                reason="Conservation mode - harvest approaching"
            ))
    
    else:
        # CRISIS MODE: Intelligent rationing required
        # Calculate priority scores for each astronaut
        astronaut_scores = []
        
        for astronaut in astronauts:
            if not astronaut['alive']:
                continue
            
            # Priority score based on health (0-100, higher = more critical need)
            score = 0
            
            # Factor 1: Cognitive performance (0-30 points)
            # Lower cognitive = higher priority (need food to recover)
            cognitive = astronaut['cognitive']
            if cognitive < 0.3:
                score += 30  # Critical cognitive impairment
            elif cognitive < 0.5:
                score += 20
            elif cognitive < 0.7:
                score += 10
            
            # Factor 2: Calorie deficit (0-25 points)
            deficit_days = astronaut['calorie_deficit_days']
            if deficit_days > 20:
                score += 25  # Severe deficit
            elif deficit_days > 10:
                score += 15
            elif deficit_days > 5:
                score += 8
            
            # Factor 3: Micronutrient score (0-20 points)
            micro = astronaut['micronutrient_score']
            if micro < 0.3:
                score += 20  # Severe deficiency
            elif micro < 0.5:
                score += 12
            elif micro < 0.7:
                score += 6
            
            # Factor 4: Immune system (0-15 points)
            immune = astronaut['immune']
            if immune < 0.5:
                score += 15
            elif immune < 0.7:
                score += 8
            
            # Factor 5: Emergency rations remaining (0-10 points)
            # Prioritize those with less emergency food
            emergency_days = astronaut['emergency_food_days']
            if emergency_days < 5:
                score += 10
            elif emergency_days < 15:
                score += 5
            
            astronaut_scores.append({
                'astronaut': astronaut,
                'score': score
            })
        
        # Sort by priority score (highest need first)
        astronaut_scores.sort(key=lambda x: -x['score'])
        
        # Allocate food
        # Minimum survival: 1500 kcal/day per person
        minimum_total = alive_count * 1500
        
        if total_available / days_until_harvest >= minimum_total:
            # Can give everyone minimum + distribute extra by priority
            daily_budget = total_available / days_until_harvest
            allocated = 0
            
            for item in astronaut_scores:
                astronaut = item['astronaut']
                score = item['score']
                
                # Base allocation: 1500 kcal (survival minimum)
                base_allocation = 1500.0
                
                # Extra allocation based on priority (up to 1500 more)
                # Highest priority gets most extra
                max_extra = 1500.0
                priority_factor = score / 100.0  # Normalize to 0-1
                extra_allocation = max_extra * priority_factor
                
                total_allocation = base_allocation + extra_allocation
                
                # Cap at 3000 kcal
                total_allocation = min(3000.0, total_allocation)
                
                # Ensure we don't exceed daily budget
                if allocated + total_allocation > daily_budget:
                    total_allocation = max(1500.0, daily_budget - allocated)
                
                allocated += total_allocation
                
                reason = f"Crisis rationing - Priority score: {score:.0f}"
                if score > 70:
                    reason = "CRITICAL: Severe health decline"
                elif score > 50:
                    reason = "HIGH: Significant health concerns"
                elif score > 30:
                    reason = "MODERATE: Health monitoring required"
                else:
                    reason = "STABLE: Reduced rations"
                
                plans.append(RationPlan(
                    astronaut_name=astronaut['name'],
                    calories_allocated=total_allocation,
                    protein_allocated_g=total_allocation * 0.0375,  # 15% protein
                    priority_score=score,
                    reason=reason
                ))
        else:
            # EXTREME CRISIS: Can't even give minimum to everyone
            # Triage: Focus resources on most viable survivors
            daily_budget = total_available / days_until_harvest
            
            # Sort by inverse priority - save the healthiest
            astronaut_scores.sort(key=lambda x: x['score'])
            
            allocated = 0
            for item in astronaut_scores:
                astronaut = item['astronaut']
                
                # Try to give 2000 kcal to healthiest until budget runs out
                allocation = min(2000.0, daily_budget - allocated)
                if allocation < 1000:
                    allocation = 0  # Not enough to help
                
                allocated += allocation
                
                plans.append(RationPlan(
                    astronaut_name=astronaut['name'],
                    calories_allocated=allocation,
                    protein_allocated_g=allocation * 0.0375,
                    priority_score=item['score'],
                    reason="TRIAGE: Extreme food shortage" if allocation > 0 else "TRIAGE: Insufficient resources"
                ))
                
                if allocated >= daily_budget:
                    break
    
    return plans


def calculate_harvest_priority(plants: list, food_shortage_severity: float) -> List[Tuple[str, int, str]]:
    """
    Determine which plants to harvest and in what order.
    
    Returns: List of (plant_name, priority, reason)
    priority: 1=harvest now, 2=harvest soon, 3=wait
    """
    priorities = []
    
    for plant in plants:
        if not plant['harvestable']:
            continue
        
        # Calculate harvest value score
        expected_yield = plant['expected_yield_kg']
        
        # Caloric value per kg
        calorie_per_kg = {
            "Potato": 770,
            "Beans": 1000,
            "Radish": 160,
            "Lettuce": 150,
            "Herbs": 230
        }
        
        total_calories = expected_yield * calorie_per_kg.get(plant['name'], 500)
        
        # Priority factors
        if food_shortage_severity > 0.8:  # Critical shortage
            priority = 1
            reason = f"URGENT: Food crisis - {total_calories:.0f} kcal needed"
        elif food_shortage_severity > 0.5:  # Moderate shortage
            if total_calories > 5000:  # High-value crop
                priority = 1
                reason = f"High-value harvest - {total_calories:.0f} kcal"
            else:
                priority = 2
                reason = f"Moderate harvest - {total_calories:.0f} kcal"
        else:  # Adequate food
            if plant['hydration'] < 50:  # Plant declining
                priority = 1
                reason = "Harvest before quality degrades"
            else:
                priority = 2
                reason = "Optimal harvest window"
        
        priorities.append((plant['name'], priority, reason))
    
    # Sort by priority
    priorities.sort(key=lambda x: x[1])
    
    return priorities
