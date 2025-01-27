

import pandas as pd
from shared_logic import generate_accounts_df
from dbio import sql
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, PULP_CBC_CMD

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
    problem += lpSum(x[i,j] for i in range(len(l1)) for j in range(len(l2))), "Objective"

    # Solve the problem
    solver = PULP_CBC_CMD(msg=False)
    problem.solve(solver)

    # Collect the solution
    solution = {var.name: var.varValue for var in problem.variables()}
    return solution

# Example usage
# l1 = [79, 20, 1]  # Corresponds to s, p, i
# l2 = [20, 30, 40, 5, 5]  # Corresponds to f, k, r, l, e
# l3 = [(0, 0), (1, 0), (0, 1), (2, 1), (0, 2), (0, 3), (2, 3), (0, 4)]  # Connections

# solution = solve_lp(l1, l2, l3)

# print("Solution:", solution)

# for i in range(len(l1)):
#     print("i:", l1[i])
#     s = 0
#     for j in range(len(l2)):
#         num = round(l1[i] * solution[f"x{i}{j}"], 2)
#         s += num
#         if num > 0: print(f"{l1[i]} * {solution[f'x{i}{j}']}:  {num}")
#     print("sum:", s)

# print()
# for j in range(len(l2)):
#     print("j:", l2[j])
#     s = 0
#     for i in range(len(l1)):
#         num = round(l1[i]*solution[f"x{i}{j}"], 2)
#         s += num
#         if num > 0: print(f"{l1[i]} * {solution[f'x{i}{j}']}:  {num}")
#     print("sum:", s)
    

# # Input is the generated dataframe that has all the percentages on it
# # We're trying to allocate the income percentages to the budget percentages which will
# # Output will be that same table with additional columns showing the percentages

# # Want to prioritize budgets that have less incomes allocated to them
# # After that prioritze usings the incomes that are assigned to the least things
# # After that prioritize the ones that have the most percentage
def determine_budget_allocations(df: pd.DataFrame, income: pd.DataFrame, budget: pd.DataFrame):

    # print(income)
    # print(budget)
    # print(df)

    df['Percentage'] = df['Percentage']*100

    l1 = df[df['Category'] == 'income']['Percentage'].tolist()
    l1_name = df[df['Category'] == 'income']['Name'].tolist()
    l2 = df[df['Category'] != 'income']['Percentage'].tolist()
    l2_name = df[df['Category'] != 'income']['Name'].tolist()

    # print(l1_name)
    l3 = []
    for i, row in income.iterrows():
        for b in row['budgets'].split(', '):
            l3 += [(l1_name.index(row['name']), l2_name.index(b))]
        l3 += [(l1_name.index(row['name']), l2_name.index('Leftover'))]

    solution = solve_lp(l1, l2, l3)

    # print(solution)

    for i in range(len(l1)):
        # print("i:", l1[i])
        s = 0
        for j in range(len(l2)):
            num = l1[i] * solution[f"x{i}{j}"]
            s += num
            df.loc[df['Name'] == l2_name[j], f"{l1_name[i]} %"] = solution[f"x{i}{j}"]
            # if num > 0: print(f"{l1[i]} * {solution[f'x{i}{j}']}:  {round(num, 2)}")
        if round(l1[i] - s, 2) > 0: print(f"WARNING: {l1[i]} - {s}:  {round(l1[i] - s, 2)}")
        # print("sum:", round(s, 2))

    # print()
    for j in range(len(l2)):
        # print("j:", l2[j])
        s = 0
        for i in range(len(l1)):
            num = l1[i]*solution[f"x{i}{j}"]
            s += num
            # if num > 0: print(f"{l1[i]} * {solution[f'x{i}{j}']}:  {round(num, 2)}")
        if round(l2[j] - s, 2) > 0: print(f"WARNING: {l2[j]} - {s}:  {round(l2[j] - s, 2)}")
        # print("sum:", round(s, 2))

    return df




determine_budget_allocations(generate_accounts_df(), sql.get_income(), sql.get_budget())

sql.close()