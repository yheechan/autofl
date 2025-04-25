import re
import tiktoken

def drop_base_name(name):
    if "." in name:
        # a.b.c -> a.b
        return ".".join(name.split(".")[:-1])
    else:
        # a -> .
        return "."

def get_base_name(name):
    # a.b.c -> c
    return name.split(".")[-1]

def parse_arguments(arg_string):
    arguments = []
    current_argument = ""
    angle_bracket_count = 0

    for char in arg_string:
        if char == ',' and angle_bracket_count == 0:
            arguments.append(current_argument.strip())
            current_argument = ""
        else:
            current_argument += char
            if char == '<':
                angle_bracket_count += 1
            elif char == '>':
                angle_bracket_count -= 1

    if current_argument:
        arguments.append(current_argument.strip())

    return arguments

def is_method_signature(expr: str) -> bool:
    m = re.match(r"\S+\(.*\)", expr)
    return m is not None

def get_method_name_and_argument_types(expr: str) -> tuple:
    m = re.match(r"(\S+)\((.*)\)", expr)
    if m: # is a form of method(args)
        method_name = m.group(1)
        arguments = parse_arguments(m.group(2).strip())
    else:
        method_name = expr
        arguments = []
    argument_types = []
    for arg in arguments:
        # qualitifed type -> short type
        arg_type = re.sub(re.compile(r'[\w+\.]*\.(\w+)\s*\w*'), r'\1', arg)
        # remove arg name if exists
        arg_type = re.sub(re.compile(r' \w+$'), '', arg_type)
        argument_types.append(arg_type)

    method_name_lst = method_name.split('.')
    # replace <init> with class name
    if method_name_lst[-1] == "<init>" and len(method_name_lst) > 1:
        class_name = method_name_lst[-2]
        method_name_lst = method_name_lst[:-1] + [class_name]

    return method_name_lst, argument_types

def get_method_name(signature, simple_name=True):
    method_name_lst, _ = get_method_name_and_argument_types(signature)
    if simple_name:
        return method_name_lst[-1]
    else:
        return ".".join(method_name_lst)

def name_matcher(short_name, full_name): # modified
    # ex) `java.lang.Object` matches with `java.lang.Object`, `lang.Object`, `Object`,
    # not with `bject` or `ang.Object`
    type_depth = len(short_name) - 1
    truncated_full_name = full_name[-type_depth-1:]
    return short_name == truncated_full_name

def get_method_name_and_args_for_c_cpp(expr: str) -> tuple:
    method_sign = expr
    if "." in expr.split("(")[0]:
        expr = expr.split("(")[0].replace(".", "::") + "(" + expr.split("(")[1]
    if "::" in expr.split("(")[0]:
        method_sign = expr.split("(")[0].split("::")[-1] + "(" + expr.split("(", 1)[1]
    
    m = re.match(r"(\S+)\((.*)\)", method_sign)

    if m: # is a form of method(args)
        method_name = m.group(1)
        arguments = parse_arguments(m.group(2).strip())
    
    return method_name, arguments


def lenient_matcher(pred_expr, gt_answer):
    if pred_expr == gt_answer: # Exact Matching
        return True

    try:
        pred_method_name, pred_arg_types = get_method_name_and_argument_types(pred_expr)
    except:
        return False # not a valid signature

    gt_method_name, gt_arg_types = get_method_name_and_argument_types(gt_answer)

    return len(pred_method_name) >= 2 \
        and name_matcher(pred_method_name, gt_method_name) \
        and gt_arg_types == pred_arg_types

def lenient_matcher_for_c_cpp(pred_expr, gt_answer, threshold=0):
    if pred_expr == gt_answer: # Exact Matching
        return True
    
    try:
        pred_method_name, pred_args = get_method_name_and_args_for_c_cpp(pred_expr)
        gt_method_name, gt_args = get_method_name_and_args_for_c_cpp(gt_answer)

        arg_diff = abs(len(pred_args) - len(gt_args))
        if arg_diff <= threshold and pred_method_name == gt_method_name:
            return True
        else:
            return False
    except:
        return False # not a valid signature
        

def python_lenient_matcher(pred, buggy_method):
    return pred.split('(')[0] == buggy_method.split('(')[0]

def count_chat_tokens(messages, model="gpt-4-turbo"):
    """Accurately count tokens used by OpenAI chat models like gpt-3.5-turbo or gpt-4-turbo."""
    encoding = tiktoken.encoding_for_model(model)

    # Rules based on OpenAI's documentation
    tokens_per_message = 3  # every message: <|start|>{role/name}\n{content}<|end|>
    tokens_per_name = 1     # if name is present

    total_tokens = 0
    for message in messages:
        total_tokens += tokens_per_message
        for key, value in message.items():
            if key == "function_call" and isinstance(value, dict):
                for k, v in value.items():
                    total_tokens += len(encoding.encode(k))
                    total_tokens += len(encoding.encode(str(v)))
            else:
                total_tokens += len(encoding.encode(str(value)))
                if key == "name":
                    total_tokens += tokens_per_name

    total_tokens += 3  # priming for reply: assistant role tag
    return total_tokens