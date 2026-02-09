from data_utils import refine
from LLM_Gateway import nexa_ai
import pandas as pd
import json
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import START, END, StateGraph
from typing import TypedDict

# ------------------------------
# COLORED DEBUG LOGGER
# ------------------------------
class LogColors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log_header(title):
    print(f"\n{LogColors.BOLD}{LogColors.HEADER}========== {title} =========={LogColors.END}")

def log_info(msg):
    print(f"{LogColors.BLUE}[INFO]{LogColors.END} {msg}")

def log_success(msg):
    print(f"{LogColors.GREEN}[SUCCESS]{LogColors.END} {msg}")

def log_warning(msg):
    print(f"{LogColors.YELLOW}[WARNING]{LogColors.END} {msg}")

def log_error(msg):
    print(f"{LogColors.RED}[ERROR]{LogColors.END} {msg}")

def log_debug(msg):
    print(f"{LogColors.CYAN}[DEBUG]{LogColors.END} {msg}")


class AgentState(TypedDict):
    data_path:str
    dataset: pd.DataFrame
    unique_transactions: pd.DataFrame
    rules: dict

llm = nexa_ai()
def retrieve_file():
    pass

def preprocess(state:AgentState):
    log_header("Starting Ingestion Pipline")
    log_header("Pre Processing")
    datapath=state['data_path']
    data=refine(datapath)
    log_success("Pre Processing Complete")
    return {'dataset':data}

def get_unique_transactions(state:AgentState):
    log_header("Fetching Unique Transactions")
    unique_transaction=state['dataset'].groupby(by=['Reciever_Sender', 'Method'])['Remarks'].count()
    log_success("Fetching Completed")
    return {'unique_transactions':unique_transaction.reset_index()}


def rule_based_classfication(state:AgentState):
    log_header("Starting rule_based_classfication")
    unique_transactions=state['unique_transactions']

    with open('categories.json','r') as file:
        defined_categories=json.load(file)

    log_info(f"fetched rules: {defined_categories}")
    
    for pointer, name in enumerate(unique_transactions['Reciever_Sender']):
        cat=False
        for key,value in defined_categories.items():
            for already_in_category in value:
                if already_in_category.lower() in str(name):
                    cat=key
        if cat:
            unique_transactions.loc[pointer,'label']=cat
            log_debug( f"labeled {name} as {cat}" )
        else:
            unique_transactions.loc[pointer,'label']="llm"
            log_debug(f"sent {name} to llm")

        log_success("completed rule based classification")
    return {'unique_transactions':unique_transactions, 
            'rules':defined_categories}

            
def llm_based_classification(state: AgentState):
    log_header("starting llm classification")
    unique_transactions = state['unique_transactions']
    transactions = unique_transactions.loc[
        unique_transactions['label'] == 'llm'
    ]
    log_info(f"txn to llm{len(transactions)}")


    transactions_json = transactions.to_dict(orient="records")
    categories = state['rules']

    batch_size = 50

    for i in range(0, len(transactions_json), batch_size):
        batch = transactions_json[i:i + batch_size]

        prompt = f"""
        You are a highly accurate financial transaction classification engine.

        TASK:
        Classify each transaction into the MOST appropriate category using the provided rules.

        INPUT:
        - rules: {state['rules']}
        - transactions: {batch}

        IMPORTANT:
        Each transaction contains:
        - Reciever_Sender (merchant or counterparty name)
        - Method (payment method)
        - Remarks (transaction description, if available)

        CLASSIFICATION LOGIC (STRICT BUT PRACTICAL):

        1. Perform case-insensitive substring matching.
        - If any keyword from rules appears inside Reciever_Sender OR Remarks,
            it MUST be considered a valid match.
        - Example:
            keyword = "swiggy"
            Reciever_Sender = "Swiggy Instamart Pvt Ltd"
            → This IS a match.

        2. Always attempt to match an existing rule FIRST.

        3. If multiple rules match:
        - Choose the MOST SPECIFIC category.
        - Prefer the rule with the longest matching keyword.

        4. If category exists in rules but the matched keyword is new:
        → classify as "new_keyword"

        5. If NO rule matches:
        - Infer the most logical category name from the merchant or remarks.
        - The "category" field must contain the generated category name.
        - The 5th field must be "new_category".
        - DO NOT write the literal word "new_category" in the category field.


        6. Use "uncategorized" ONLY if:
        - Transaction meaning is completely unclear
        - Or it contains random/meaningless text

        7. Do NOT default to "uncategorized" if merchant name is clear.

        8. You MUST assign a meaningful category whenever possible.

        OUTPUT REQUIREMENTS (MANDATORY):

        - Return STRICT JSON only.
        - No explanations.
        - No comments.
        - No extra text.
        - No markdown.
        - No trailing commas.
        - Output must be valid JSON.

        Return EXACTLY in this format:

        [
        ["Reciever_Sender","Method","category","matched_keyword","rule_based | new_category | new_keyword"],
        ["Reciever_Sender","Method","category","matched_keyword","rule_based | new_category | new_keyword"]
        ]

        Where:
        - "category" = final assigned category
        - "matched_keyword" = exact keyword used for matching
        - "rule_based | new_category | new_keyword" =
            • "rule_based" → matched existing rule keyword
            • "new_keyword" → category exists but keyword is new
            • "new_category" → entirely new category created

        EXAMPLE:
            [
                ["LIC India","UPI","insurance","lic","new_category"],
                ["debit investments","autopay","SIP","new_category"]
            ]

        CRITICAL:
        Accuracy is more important than coverage.
        However, do NOT overuse "uncategorized".
        Only use it when transaction meaning is truly ambiguous.

        """

        response = llm.invoke(prompt)
        log_debug(response.content)
        try:
            parsed_output = JsonOutputParser().parse(response.content)
        except Exception:
            print("Unable to parse JSON for batch:", i)
            continue
        
        for txn in parsed_output:
            name, method, category, matched_keyword, tag = txn
            log_debug(f"mapped{name},{method},{category}")
            unique_transactions.loc[
                (unique_transactions['Reciever_Sender'] == name) &
                (unique_transactions['Method'] == method),
                'label'
            ] = category

            if tag == "new_category" and category not in ["uncategorized","new_category"]:
                log_info(f"adding new category: {category}")
                categories[category] = [matched_keyword]

            elif tag == "new_keyword" and matched_keyword != "":
                if category in categories:
                    if matched_keyword not in categories[category]:
                        categories[category].append(matched_keyword)

    log_success("completed llm classification")

    return {
        'rules': categories,
        'unique_transactions': unique_transactions
    }


def mapper(state: AgentState):
    log_header("mapping to database")
    dataset=state['dataset']
    unique=state['unique_transactions']

    count=0
    for row in unique.itertuples(index=True):
        dataset.loc[(dataset['Reciever_Sender']==row.Reciever_Sender) & (dataset['Method']==row.Method),'label']=row.label
        count+=1

    log_info(f"total mapped:  {count} , tatal mappings:  {len(unique)}")
    # dataset.to_csv('improved.csv')

    with open('categories.json','w') as f:
        json.dump(state['rules'],f)
    log_success("Ingestion Complete")
    return {'dataset':dataset}


graph=StateGraph(AgentState)
graph = StateGraph(AgentState)

# Add nodes
graph.add_node("preprocess", preprocess)
graph.add_node("get_unique_transactions", get_unique_transactions)
graph.add_node("rule_based_classification", rule_based_classfication)
graph.add_node("llm_based_classification", llm_based_classification)
graph.add_node("mapper", mapper)

# ---- DEFINE FLOW ----
graph.add_edge(START, "preprocess")
graph.add_edge("preprocess", "get_unique_transactions")
graph.add_edge("get_unique_transactions", "rule_based_classification")
graph.add_edge("rule_based_classification", "llm_based_classification")
graph.add_edge("llm_based_classification", "mapper")
graph.add_edge("mapper", END)

# ---- COMPILE ----
app = graph.compile()







    