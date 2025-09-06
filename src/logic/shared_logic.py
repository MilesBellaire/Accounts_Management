import sys
sys.path.append('./')

from database.io.dbio import sql
import re
import pandas as pd
from pulp import LpProblem, LpVariable, LpMinimize, LpMaximize, lpSum, PULP_CBC_CMD

def Evaluate_equation(equation: str, base: float, incomes_used=[], budgets_used=[])-> float:
    # print(equation, base, incomes_used, budgets_used)
    if equation in ('null', None, 'nan', ''): return base

    constants = sql.get_constants()
    incomes = sql.income.get()
    incomes = incomes[(incomes['unit'] == '$') | (incomes['unit'] == 'eq')]
    budgets = sql.budget.get()
    budgets = budgets[(budgets['unit'] == '$') | (budgets['unit'] == 'eq')]
    

    # print(incomes_used, budgets_used)

    split_equation = re.split(r'[\[\]]', equation.replace(' ', ''))
    filled_equation = ''


    new_incomes_used = [incomes[incomes['name'] == split]['id'].iloc[0] for split in split_equation if len(incomes[incomes['name'] == split]['id'])] + incomes_used
    new_budgets_used = [budgets[budgets['name'] == split]['id'].iloc[0] for split in split_equation if len(budgets[budgets['name'] == split]['id'])] + budgets_used

    for split in split_equation:
        if split == 'self':
            filled_equation += str(base)
        elif split in constants['name'].tolist():
            filled_equation += str(constants[constants['name'] == split]['value'].iloc[0])
        elif split in incomes['name'].tolist():
            if incomes[incomes['name'] == split]['id'].iloc[0] in incomes_used: continue
            filled_equation += str(Evaluate_equation(
                incomes[incomes['name'] == split]['equation'].iloc[0], 
                incomes[incomes['name'] == split]['value'].iloc[0],
                new_incomes_used,
                new_budgets_used
            ))
        elif split in budgets['name'].tolist():
            if budgets[budgets['name'] == split]['id'].iloc[0] in budgets_used: continue
            filled_equation += str(Evaluate_equation(
                budgets[budgets['name'] == split]['equation'].iloc[0], 
                budgets[budgets['name'] == split]['value'].iloc[0],
                new_incomes_used,
                new_budgets_used
            ))
        else:
            filled_equation += split
    # print(filled_equation)
    return eval(filled_equation) # Very unsafe

def get_dollars_per(per_month):
    return [
        '${:,.2f}'.format(per_month/30.437),
        '${:,.2f}'.format(per_month/4.345),
        '${:,.2f}'.format(per_month),
        '${:,.2f}'.format(per_month*12),
        '${:,.2f}'.format(per_month*60),
    ]

def generate_accounts_df(include_external=True):
    incomes = sql.income.get()
    budgets = sql.budget.get()

    # Drop other
    incomes = incomes[incomes['name'] != 'other']
    if not include_external:
        incomes.loc[incomes['name'] == 'salary', 'equation'] += f' * (100-{budgets[budgets['name'] == 'taxes']['value'].iloc[0]+budgets[budgets['name'] == '401k']['value'].iloc[0]})/100'
        budgets = budgets[budgets['name'] != 'taxes']
        budgets = budgets[budgets['name'] != '401k']

    columns = ['Name', 'Percentage', 'Per Month', 'Category', 'id']

    income_per_month = sum(incomes[incomes['unit'] == '$']['value'])
    income_per_month += sum([Evaluate_equation(str(income['equation']), income['value']) for i, income in incomes[incomes['unit'] == 'eq'].iterrows()])

    expenses_per_month = (sum(budgets[budgets['unit'] == '%ov']['value']/100*income_per_month)
        + sum([Evaluate_equation(str(budget['equation']), budget['value']) for i, budget in budgets[budgets['unit'] == 'eq'].iterrows()])
        + sum(budgets[budgets['unit'] == '$']['value']))
    
    leftover = income_per_month-expenses_per_month

    percent_cut_by_cap = 0
    overall_leftover_percentage = 1

    # Incomes
    accounts = [[
        income['name'], 
        income['value']/income_per_month, 
        income['value'], 
        'income',
        income['id']
    ] for i, income in incomes[incomes['unit'] == '$'].iterrows()]

    for i, income in incomes[incomes['unit'] == 'eq'].iterrows():
        expense = Evaluate_equation(str(income['equation']), income['value'])
        accounts.append([
            income['name'],
            expense/income_per_month,
            expense,
            'income',
            income['id']
        ])

    # Over Percentages
    accounts += [[
        budget['name'],
        budget['value']/100,
        budget['value']/100*income_per_month,
        budget['tags'],
        budget['id']        
    ] for i, budget in budgets[budgets['unit'] == '%ov'].iterrows()]
    
    accounts += [[
        budget['name'],
        budget['value']/income_per_month, 
        budget['value'], 
        budget['tags'],
        budget['id']
    ] for i, budget in budgets[budgets['unit'] == '$'].iterrows()]
    
    # Flat Expenses
    for i, budget in budgets[budgets['unit'] == 'eq'].iterrows():
        expense = Evaluate_equation(budget['equation'], budget['value'])
        accounts.append([
            budget['name'],
            expense/income_per_month,
            expense,
            budget['tags'],
            budget['id']
        ])
    
    # Leftover percentages with caps
    for i, budget in budgets[budgets['unit'] == '%lo-'].iterrows():
        expense = max(min(budget['value']/100*leftover, budget['cap']), 0)
        percentage = expense/income_per_month

        accounts.append([
            budget['name'],
            percentage,
            expense,
            budget['tags'],
            budget['id']
        ])
        
        percent_cut_by_cap += max((budget['value']/100-expense/leftover), 0)

    # Leftover percentages that take over other's caps
    for i, budget in budgets[budgets['unit'] == '%lo+'].iterrows():
        additional_percentage = percent_cut_by_cap/len(budgets[budgets['unit'] == '%lo+'])
        leftover_percentage = budget['value']/100 + additional_percentage
        percentage = leftover_percentage*leftover/income_per_month
        expense = percentage*income_per_month


        accounts.append([
            budget['name'],
            percentage,
            expense,
            budget['tags'],
            budget['id']
        ])

    # Leftovers
    overall_leftover_percentage = 1-sum([account[1] for account in accounts if account[3] != 'income'])
    accounts.append([
        'Leftover',
        overall_leftover_percentage,
        max(overall_leftover_percentage*(income_per_month), 0),
        'savings'
    ])
    
    return determine_budget_allocations(pd.DataFrame(accounts, columns=columns), include_external)


def solve_lp(l1, l2, l3):
    # Initialize the problem
    problem = LpProblem("MultiDimensional_Variable", LpMinimize)

    x = {(i, j): LpVariable(f"x{i}{j}", lowBound=0) for i in range(len(l1)) for j in range(len(l2))}

    for j in range(len(l2)):
        # print()
        # for i in range(len(l1)):
        #     if (i, j) in l3: print(f"{l1[i]}*X{i}{j}  ", end="")
        # print(f"<= {l2[j]}")
        problem += lpSum(l1[i]*x[i,j] for i in range(len(l1)) if (i, j) in l3) == l2[j]

    for i in range(len(l1)):
        problem += lpSum(x[i,j] for j in range(len(l2))) == 1
        

    # Objective function: Not sure why we're summing them but if it works...
    problem += lpSum(x[i,j]*(i+1)*(j+1)*l1[i] for i in range(len(l1)) for j in range(len(l2))), "Objective"

    # Solve the problem
    solver = PULP_CBC_CMD(msg=False)
    problem.solve(solver)

    # Collect the solution
    solution = {var.name: var.varValue for var in problem.variables()}
    return solution

# With this refact I want to leave out the leftover
def determine_budget_allocations(df: pd.DataFrame, include_external=True):

    income = sql.income.get()
    income = income[income['name'] != 'other']

    if not include_external:
        if 'taxes' in df['Name'].tolist(): df = df[df['Name'] != 'taxes']
        if '401k' in df['Name'].tolist(): df = df[df['Name'] != '401k']

    # df = df[df['Name'] != 'Leftover']

    # print(df)

    df['Percentage'] = df['Percentage']*1000

    # select percentage and name from a list, sort by percentage and then split into two lists l1 and l_name
    sorted_df = df[df['Category'] == 'income'].sort_values(by='Percentage', ascending=False)
    l1 = sorted_df['Percentage'].tolist()
    l1_name = sorted_df['Name'].tolist()
 
    sorted_df = df[df['Category'] != 'income'].sort_values(by='Percentage', ascending=False)
    # Move Leftover to the end
    sorted_df = pd.concat([sorted_df[sorted_df['Name'] != 'Leftover'], sorted_df[sorted_df['Name'] == 'Leftover']])
    l2 = sorted_df['Percentage'].tolist()
    l2_name = sorted_df['Name'].tolist()

    # print(l1_name)
    l3 = []
    for i, row in income.iterrows():
        for b in row['budgets'].split(', '):
            if b == '' or (not include_external and b in ('taxes', '401k')): continue
            l3 += [(l1_name.index(row['name']), l2_name.index(b))]
        l3 += [(l1_name.index(row['name']), l2_name.index('Leftover'))]

    # print(l3)

    solution = solve_lp(l1, l2, l3)

    # print(solution)

    for i in range(len(l1)):
        # print("i:", l1[i])
        s = 0
        for j in range(len(l2)):
            num = l1[i] * solution[f"x{i}{j}"]
            s += num
            df.loc[df['Name'] == l2_name[j], f"{l1_name[i]} %"] = solution[f"x{i}{j}"]
            df.loc[df['Name'] == l2_name[j], f"{l1_name[i]} $"] = solution[f"x{i}{j}"] * df.loc[df['Name'] == l1_name[i], 'Per Month'].iloc[0]
            # if num > 0: print(f"{l1[i]} * {solution[f'x{i}{j}']}:  {round(num, 2)}")
        if round(l1[i] - s, 2) > 0: print(f"LP WARNING: {l1_name[i]}: {l1[i]} - {s}:  {round(l1[i] - s, 2)}")
        # print("sum:", round(s, 2))

    for n1 in l1_name:
        for n2 in l1_name:
            # print(n1, n2)
            df.loc[df['Name'] == n2, f"{n1} %"] = 0
            df.loc[df['Name'] == n2, f"{n1} $"] = 0

    # print()
    for j in range(len(l2)):
        # print("j:", l2[j])
        s = 0
        for i in range(len(l1)):
            num = l1[i]*solution[f"x{i}{j}"]
            s += num
            df.loc[df['Name'] == l1_name[i], f"{l1_name[i]} %"] += solution[f"x{i}{j}"]
            df.loc[df['Name'] == l1_name[i], f"{l1_name[i]} $"] += solution[f"x{i}{j}"] * df.loc[df['Name'] == l1_name[i], 'Per Month'].iloc[0]
            # if num > 0: print(f"{l1[i]} * {solution[f'x{i}{j}']}:  {round(num, 2)}")
        if round(l2[j] - s, 2) > 0: print(f"LP WARNING: {l2_name[j]}: {l2[j]} - {s}:  {round(l2[j] - s, 2)}")
        # print("sum:", round(s, 2))


    df['Percentage'] = df['Percentage']/1000

    return df

# print(determine_budget_allocations(generate_accounts_df()))