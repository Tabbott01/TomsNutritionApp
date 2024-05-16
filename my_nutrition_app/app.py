import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)

# Load the food data from the provided GitHub link
food_data_url = 'https://raw.githubusercontent.com/Tabbott01/aitest/main/footdatatest1.csv'
food_data = pd.read_csv(food_data_url)

# Ensure the Energy column is numeric
food_data['Energy'] = pd.to_numeric(food_data['Energy'], errors='coerce')
food_data.dropna(subset=['Energy'], inplace=True)
food_data = food_data[food_data['Energy'] > 0]  # Filter out foods with zero calories

# Define food groups for snacks
snack_food_groups = ["AM", "AN", "AP", "BN", "FA", "GA", "SE", "SN", "BNE", "BNH", "BNS", "SEA", "SEC", "SNA", "SNB", "SNC"]

# Define food groups for lunch and dinner
lunch_dinner_food_groups = ["AB", "AE", "CD", "DR", "JR", "MBG", "MR", "WA", "WAA", "WAC", "WAE"]

# Define specific food codes for breakfast
breakfast_food_codes = ["12-940", "12-944", "12-962", "12-943", "12-963"]

# Define food codes for breakfast for energy focus
energy_breakfast_food_codes = [
    "11-792", "11-795", "11-793", "11-773", "11-774", "11-780", "11-781",
    "11-1106", "11-1107", "11-1108", "12-940", "12-944", "12-962", "12-943", "12-963"
]

# Define food groups for lunch and dinner for energy focus
energy_lunch_dinner_food_groups = ["CD", "DR", "JR", "MR", "WA", "WAA", "WAC", "WAE"]

def calculate_bmr(weight, height, age, gender):
    if gender == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    elif gender == 'female':
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    else:
        raise ValueError("Gender must be 'male' or 'female'")
    return bmr

def calculate_daily_caloric_intake(weight, height, age, gender, activity_level):
    bmr = calculate_bmr(weight, height, age, gender)
    activity_multiplier = {
        'sedentary': 1.2,
        'lightly active': 1.375,
        'moderately active': 1.55,
        'very active': 1.725,
        'extra active': 1.9
    }
    if activity_level not in activity_multiplier:
        raise ValueError("Activity level must be one of: 'sedentary', 'lightly active', 'moderately active', 'very active', 'extra active'")
    
    daily_caloric_intake = bmr * activity_multiplier[activity_level]
    return daily_caloric_intake

def recommend_meal_plan(daily_caloric_intake, food_data, wellbeing_focus=False, energy_focus=False, dietary_restriction='none'):
    if wellbeing_focus:
        meal_distribution = {
            'breakfast': 0.20,
            'lunch': 0.30,
            'snack1': 0.10,
            'dinner': 0.30,
            'snack2': 0.10
        }
    else:
        meal_distribution = {
            'breakfast': 0.20,
            'lunch': 0.35,
            'dinner': 0.35,
            'snacks': 0.10
        }
    
    meal_plan = {}
    for meal, percentage in meal_distribution.items():
        target_calories = daily_caloric_intake * percentage
        lower_bound = target_calories * 0.75
        upper_bound = target_calories * 1.25
        
        # Apply food group filters based on dietary restrictions
        if dietary_restriction == 'nut_allergy' and meal == 'snacks':
            filtered_food_data = food_data[~food_data['Group'].isin(["GA"])]
        elif dietary_restriction == 'vegetarian' and meal in ['lunch', 'dinner']:
            filtered_food_data = food_data[~food_data['Group'].isin(["AE", "AB", "JR", "MBG", "MR", "WA", "WAA", "WAC", "WAE"])]
        elif dietary_restriction == 'pescatarian' and meal in ['lunch', 'dinner']:
            filtered_food_data = food_data[~food_data['Group'].isin(["AE", "AB", "MBG", "MR", "WA", "WAA", "WAC", "WAE"])]
        else:
            filtered_food_data = food_data

        # Further apply food group filters for wellbeing and energy focuses
        if wellbeing_focus and meal in ['snack1', 'snack2']:
            filtered_food_data = filtered_food_data[filtered_food_data['Group'].isin(["FA", "FC"])]
        elif energy_focus and meal == 'snacks':
            filtered_food_data = filtered_food_data[filtered_food_data['Group'].isin(["FA", "FC"])]
        elif energy_focus and meal == 'breakfast':
            filtered_food_data = filtered_food_data[filtered_food_data['Food_Code'].isin(energy_breakfast_food_codes)]
        elif energy_focus and meal in ['lunch', 'dinner']:
            filtered_food_data = filtered_food_data[filtered_food_data['Group'].isin(energy_lunch_dinner_food_groups)]
        elif meal == 'snacks':
            filtered_food_data = filtered_food_data[filtered_food_data['Group'].isin(snack_food_groups)]
        elif meal == 'breakfast':
            filtered_food_data = filtered_food_data[(filtered_food_data['Group'] == "AI") | (filtered_food_data['Food_Code'].isin(breakfast_food_codes))]
        elif meal in ['lunch', 'dinner']:
            filtered_food_data = filtered_food_data[filtered_food_data['Group'].isin(lunch_dinner_food_groups)]
        else:
            filtered_food_data = filtered_food_data
        
        suitable_meals = []
        
        for _, food in filtered_food_data.iterrows():
            food_name = food['Food_Name']
            calories_per_100g = food['Energy']
            
            if calories_per_100g <= 0:
                continue
            
            # Calculate the weight needed to meet the target calories, rounded to the nearest multiple of 10
            required_weight = round((target_calories / calories_per_100g) * 100 / 10) * 10
            
            # Set weight range limits
            if wellbeing_focus and meal in ['snack1', 'snack2']:
                weight_min, weight_max = 50, 500
            else:
                weight_min, weight_max = 50, 1000

            # Ensure the portion size is within the reasonable range
            if weight_min <= required_weight <= weight_max and lower_bound <= required_weight * (calories_per_100g / 100) <= upper_bound:
                suitable_meals.append({
                    'name': food_name,
                    'calories': calories_per_100g,
                    'weight': required_weight
                })
        
        if len(suitable_meals) >= 3:
            recommended_meals = pd.DataFrame(suitable_meals).sample(3)
        else:
            recommended_meals = pd.DataFrame(suitable_meals)
        
        meal_plan[meal] = []
        for _, recommended_meal in recommended_meals.iterrows():
            total_calories = (recommended_meal['calories'] / 100) * recommended_meal['weight']
            meal_plan[meal].append({
                'name': recommended_meal['name'],
                'calories_per_100g': recommended_meal['calories'],
                'weight': recommended_meal['weight'],
                'total_calories': total_calories,
                'target_calories': target_calories
            })
    
    return meal_plan

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        weight = float(request.form['weight'])
        weight_unit = request.form['weight_unit']
        height = float(request.form['height'])
        height_unit = request.form['height_unit']
        age = int(request.form['age'])
        gender = request.form['gender']
        activity_level = request.form['activity_level']
        wellbeing_focus = 'wellbeing_focus' in request.form
        energy_focus = 'energy_focus' in request.form
        dietary_restriction = request.form['dietary_restriction']
        
        # Convert weight to kg if necessary
        if weight_unit == 'lb':
            weight = weight * 0.453592
        
        # Convert height to cm if necessary
        if height_unit == 'inches':
            height = height * 2.54
        
        daily_caloric_intake = calculate_daily_caloric_intake(weight, height, age, gender, activity_level)
        # Round daily caloric intake to the nearest multiple of 5
        daily_caloric_intake = round(daily_caloric_intake / 5) * 5
        meal_plan = recommend_meal_plan(daily_caloric_intake, food_data, wellbeing_focus, energy_focus, dietary_restriction)
        
        return render_template('index.html', meal_plan=meal_plan, daily_caloric_intake=daily_caloric_intake)
    
    return render_template('index.html', meal_plan=None)

@app.route('/info')
def info():
    return render_template('info.html')

if __name__ == '__main__':
    app.run(debug=True)
