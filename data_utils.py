import pandas as pd
import re

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


def refine_str(content: str):
    content=content.strip().lower()
    refined_content=re.sub(r'\n', '', content)
    return refined_content

def debit_credit_refine(content: str):
    if content=='cr':
        return "credit"
    else:
        return "debit"
    
def classify_method(content: str):
    method=""
    temp=content.split(" ")
    comparator=[]
    for text in temp:
        comparator.append(text.strip().lower())
    
    ##mode of payment
    if "upi" in comparator:
        method+="upi "
    elif ["atm", "atmcard","csh", "cash"] in comparator:
        method+="atm "
    elif ['neft'] in comparator:
        method+="neft "
    else:
        ""
    #action
    if ["dep","deposit"] in comparator:
        method+="credit "
    else:
        method+="debit "

    if "hdfcmf" in comparator:
        method+="investment"
    if "cemtex" in comparator:
        method+="bulk payment "
    log_debug(f"comparator:{comparator}")
    log_debug(f"method:{method}")

    return method
    


def refine(dataset_path:str):
    log_info("data refining")
    if dataset_path.split('.')[-1] == 'xlsx':
        data=pd.read_excel(dataset_path)
    else:
        data=pd.read_csv(dataset_path)

    details=list(data['Details'])

    temp2 = {
            'Method':[],
            'Debit_Credit':[],
            'TransactionID':[],
            'Reciever_Sender':[],
            'Reciever_Sender_Bank':[],
            'Reciever_Sender_Details':[],
            'Remarks':[]
        }
    for i in range(len(details)):
        temp=details[i].split('/')
        if len(temp)==7:
            temp2['Method'].append(classify_method(refine_str(temp[0])))
            temp2['Debit_Credit'].append(debit_credit_refine(refine_str(temp[1])))
            temp2['TransactionID'].append(refine_str(temp[2]))
            temp2['Reciever_Sender'].append(refine_str(temp[3]))
            temp2['Reciever_Sender_Bank'].append(refine_str(temp[4]))
            temp2['Reciever_Sender_Details'].append(refine_str(temp[5]))
            temp2['Remarks'].append(refine_str(temp[6]))
        else:
            temp2['Method'].append(classify_method(refine_str(details[i])))
            temp2['Debit_Credit'].append("N/A")
            temp2['TransactionID'].append("N/A")
            temp2['Reciever_Sender'].append("N/A")
            temp2['Reciever_Sender_Bank'].append("N/A")
            temp2['Reciever_Sender_Details'].append("N/A")
            temp2['Remarks'].append("N/A")
    
    for key, value in temp2.items():
        data[key]=value
    log_success("refinement complete")
    return data



        
