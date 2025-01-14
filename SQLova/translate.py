from sqlova.utils.utils_wikisql import load_wikisql_data

import pandas as pd 
import os 
import json
from copy import deepcopy
import argparse
from tqdm.auto import tqdm

def replace_value_with_h_wv(data: list, tables: dict, header: bool = True):
    """
    Replace header and where-values in question into token value

    Arguments
    ---------
    data: list, data list 
    tables: dict, tables infomation
    header: bool, whether include header token or not

    Returns
    -------
    data: list, questions with token of header and where-values
    total_wv_in_q_lst: list, where-values used in question of data point
    h_in_q_lst: list, header used in question of data point
    """
    total_wv_in_q_lst = [] # total where value in question
    h_in_q_lst = [] # header in question 
    for idx, d in enumerate(data):
        # where value
        wv_in_q_lst = []
        question = d['question']
        for i, c in enumerate(d['sql']['conds']):
            wv = str(c[2]) # where value

            # find start index
            start_idx = question.lower().find(wv.lower())

            # where value is not in question
            if start_idx==-1:
                continue 

            # wv_in_q is where-value in question
            wv_in_q = question[start_idx:start_idx+len(wv)]
            
            # replace where value in question with [V{idx}]
            number_dict = {
                0: '영',
                1: '일',
                2: '이',
                3: '삼'
            } 
            question = question[:start_idx] + f'[똥{number_dict[i]}]' + question[start_idx+len(wv):]
            wv_in_q_lst.append(wv_in_q)


        data[idx]['question'] = question
        
        total_wv_in_q_lst.append(wv_in_q_lst)
        
        # header
        h = tables[d['table_id']]['header'][d['sql']['sel']].lower()
        if (h in d['question'].lower()) and (header):
            # find start index 
            start_idx = d['question'].lower().find(h.lower())
            
            # header in question
            h_in_q = d['question'][start_idx:start_idx+len(h)]
            
            # replace header in question with [H]
            data[idx]['question'] = data[idx]['question'][:start_idx] + '[허]' + data[idx]['question'][start_idx+len(h):]
            
            h_in_q_lst.append(h_in_q)
        else:
            h_in_q_lst.append(None)

    
    
    return data, total_wv_in_q_lst, h_in_q_lst

def replace_value_with_v_from_table(data: list, tables: dict, header: bool = False):
    """
    Replace header and where-values in question into token value from table

    Arguments
    ---------
    data: list, data list 
    tables: dict, tables infomation
    header: bool, whether include header token or not

    Returns
    -------
    data: list, questions with token of header and where-values
    total_v_in_q: list, values used in question of data point
    """
    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            pass

        try:
            import unicodedata
            unicodedata.numeric(s)
            return True
        except (TypeError, ValueError):
            pass
        return False

    number_dict = {
        0: '영',
        1: '일',
        2: '이',
        3: '삼',
        4: '사',
        5: '오',
        6: '육',
        7: '칠',
        8: '팔',
    } 

    total_v_in_q = {'v':[], 'h':[]}

    # from where-value
    for wv_idx, d in enumerate(data):
        wv_in_q_lst = []
        question = d['question']
        
        # loop conditions
        for i, c in enumerate(d['sql']['conds']):
            wv = str(c[2])
            
            # find start index
            start_idx = question.lower().find(wv.lower())

            if start_idx == -1:
                continue
            
            # where value in question
            wv_in_q = question[start_idx:start_idx+len(wv)]

            # replace where value token
            question = question[:start_idx] + f'[똥{number_dict[i]}]' + question[start_idx+len(wv):]

            # insert new question
            data[wv_idx]['question'] = question
            wv_in_q_lst.append(wv_in_q)

        total_v_in_q['v'].append(wv_in_q_lst)
    

    # from table
    for t_idx, d in enumerate(data):
        v_in_q_lst = total_v_in_q['v'][t_idx]
        question = d['question']
        
        # unique values in table
        value_lst = set(sum(tables[d['table_id']]['rows'], []))

        # index
        find_idx = len(v_in_q_lst)

        # loop unique values
        for i, v in enumerate(value_lst):
            # only string value
            if not is_number(v):
                if v.lower() in question.lower():
                    # find start index of table value
                    start_idx = question.lower().find(v.lower())
                    # 단어 검사
                    prev_next_p1 = question[start_idx-1:start_idx+len(v)+1].lower().strip()
                    if (start_idx!=0) and ((prev_next_p1 == v.lower()) or ('?' in prev_next_p1) or (',' in prev_next_p1)):
                        # insert value token
                        question = question[:start_idx] + f'[똥{number_dict[find_idx]}]' + question[start_idx + len(v):]
                        v_in_q_lst.append(v)
                        find_idx+=1
                        
        if header:
            headers = tables[d['table_id']]['header']
            
            h_in_q_lst = []
            for i, h in enumerate(headers):
                if h.lower() in question.lower():
                    # find start index of header
                    start_idx = question.lower().find(h.lower())
                    
                    # header in question
                    h_in_q = question[start_idx:start_idx+len(h)]
                    
                    
                    # insert header token
                    question = question[:start_idx] + f'[허{number_dict[len(h_in_q_lst)]}]' + question[start_idx+len(h):]
                    h_in_q_lst.append(h_in_q)


            total_v_in_q['h'].append(h_in_q_lst)
            
        data[t_idx]['question'] = question
        total_v_in_q['v'][t_idx] = v_in_q_lst
        
    return data, total_v_in_q
    

def extract_question(name: str, data: list, savedir: str): 
    """
    Extract question from data and save to excel file

    Argument
    --------
    name: str, dataset name ['train','dev','test']
    data: list, data list 
    savedir: str, directory to save file
    """
    # define path to save file
    filepath = os.path.join(savedir,f'{name}_question.xlsx')

    # remove '\xa0'
    questions = [" ".join(d['question'].split()) for d in data]

    # save question dataframe 
    question_df = pd.DataFrame({'question':questions})
    question_df.to_excel(filepath,index=False)


def save_token_question_and_info(name: str, datadir: str, savedir: str, header: bool = True, from_table: bool = False):
    """
    Save question with token and information

    Argumnets
    ---------
    name: str, dataset name ['train','dev','test']
    datadir: str, saved data directory
    savedir: str, directory to save data
    header: bool, whether include header token or not
    from_table: bool, whether find values from table
    """
    
    token_info = {name:{}}
    # load data
    data, tables = load_wikisql_data(path_wikisql=datadir, mode=name, no_tok=True, no_hs_tok=True)
    # transform
    if from_table:
        data_with_token, total_in_q_dict = replace_value_with_v_from_table(data=deepcopy(data), tables=tables, header=header)    
        # save
        extract_question(name=name, data=data_with_token, savedir=savedir)

        token_info[name]['v'] = total_in_q_dict['v']
        token_info[name]['h'] = total_in_q_dict['h']
    else:
        data_with_token, total_wv_in_q_lst, h_in_q_lst = replace_value_with_h_wv(data=deepcopy(data), tables=tables, header=header)
        # save
        extract_question(name=name, data=data_with_token, savedir=savedir)
        
        token_info[name]['wv'] = total_wv_in_q_lst
        token_info[name]['h'] = h_in_q_lst
    
    json.dump(token_info, open(os.path.join(savedir,f'{name}_token_info.json'),'w'), indent=4)
    print(f'Complete {name.upper()}')


def insert_replace_v_with_value_from_table(name: str, datadir:str, savedir: str, header: bool):
    """
    Insert Korean questions in data

    Argument
    --------
    name: str, dataset name ['train','dev','test']
    datadir: str, saved data directory
    savedir: str, directory to save file
    header: bool, whether include header token or not
    """
    # define path to save file
    ko_filepath = os.path.join(savedir,f'ko_{name}_question.txt')
    filepath = os.path.join(savedir,f'{name}.jsonl')

    assert os.path.isfile(ko_filepath), f'ko_{name}_question.txt does not exist.'

    # load English data
    data, _ = load_wikisql_data(path_wikisql=datadir, mode=name, no_tok=True, no_hs_tok=True)

    # read Korean questions
    with open(ko_filepath,'r') as f:
        ko_question = f.readlines()
        ko_question = list(map(lambda x: x.replace('\n',''), ko_question))

    # load token information
    token_info = json.load(open(os.path.join(savedir, f'{name}_token_info.json'),'r'))

    # replace token with values
    for idx, d in enumerate(ko_question):
        if token_info[name]['v'][idx] != []:
            for i, v in enumerate(token_info[name]['v'][idx]):
                number_dict = {
                    0: '영',
                    1: '일',
                    2: '이',
                    3: '삼',
                    4: '사',
                    5: '오',
                    6: '육',
                    7: '칠', 
                    8: '팔' # 8까지 확인
                } 
                ko_question[idx] = ko_question[idx].replace(f'[똥{number_dict[i]}]', v)

        if header:
            if token_info[name]['h'][idx] != []:
                for i, h in enumerate(token_info[name]['h'][idx]):
                    number_dict = {
                        0: '영',
                        1: '일',
                        2: '이',
                        3: '삼',
                        4: '사',
                        5: '오',
                        6: '육',
                        7: '칠', 
                        8: '팔' 
                    } 
                    ko_question[idx] = ko_question[idx].replace(f'[허{number_dict[i]}]', h)
                 
    # insert Korean questions in data
    for i in range(len(data)):
        data[i]['question'] = ko_question[i]

    # save Korean data
    with open(filepath, 'w', encoding='utf-8') as f:
        for line in data:
            json_record = json.dumps(line, ensure_ascii=False)
            f.write(json_record + '\n')
        print('Write {} records to {}'.format(len(data), filepath))

def insert_replace_h_wv_with_value(name: str, datadir:str, savedir: str, header: bool = True):
    """
    Insert Korean questions in data

    Argument
    --------
    name: str, dataset name ['train','dev','test']
    datadir: str, saved data directory
    savedir: str, directory to save file
    header: bool, whether include header token or not
    """
    # define path to save file
    ko_filepath = os.path.join(savedir,f'ko_{name}_question.txt')
    filepath = os.path.join(savedir,f'{name}.jsonl')

    assert os.path.isfile(ko_filepath), f'ko_{name}_question.txt does not exist.'

    # load English data
    data, _ = load_wikisql_data(path_wikisql=datadir, mode=name, no_tok=True, no_hs_tok=True)

    # read Korean questions
    with open(ko_filepath,'r') as f:
        ko_question = f.readlines()
        ko_question = list(map(lambda x: x.replace('\n',''), ko_question))

    # load token information
    token_info = json.load(open(os.path.join(savedir, f'{name}_token_info.json'),'r'))

    # replace token with values
    for idx, d in enumerate(ko_question):
        if ('[허]' in d) and (header):
            ko_question[idx] = ko_question[idx].replace('[허]', token_info[name]['h'][idx])

        if token_info[name]['wv'][idx] != []:
            for i, wv in enumerate(token_info[name]['wv'][idx]):
                number_dict = {
                    0: '영',
                    1: '일',
                    2: '이',
                    3: '삼'
                }
                ko_question[idx] = ko_question[idx].replace(f'[똥{number_dict[i]}]', wv)
                 
    # insert Korean questions in data
    for i in range(len(data)):
        data[i]['question'] = ko_question[i]

    # save Korean data
    with open(filepath, 'w', encoding='utf-8') as f:
        for line in data:
            json_record = json.dumps(line, ensure_ascii=False)
            f.write(json_record + '\n')
        print('Write {} records to {}'.format(len(data), filepath))


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='train,dev,test', help='dataset names')
    parser.add_argument('--replace', type=str, choices=['value','token'], help='value: replace value with token, token: replace token with value')
    parser.add_argument('--datadir', type=str, default='./data/raw', help='wikisql data directory')
    parser.add_argument('--savedir', type=str, default='./data/ko_token', help='data directory to save file')
    parser.add_argument('--header', action='store_true', help='include header token')
    parser.add_argument('--from_table', action='store_true', help='replace value with token from table')
    args = parser.parse_args()

    if not os.path.isdir(args.savedir):
        os.makedirs(args.savedir)

    dataset_names = args.dataset.split(',')

    if args.replace == 'value':
        for name in dataset_names:
            save_token_question_and_info(name=name, datadir=args.datadir, savedir=args.savedir, header=args.header, from_table=args.from_table)

    elif args.replace == 'token':
        for name in dataset_names:
            if args.from_table:
                insert_replace_v_with_value_from_table(name=name, datadir=args.datadir, savedir=args.savedir, header=args.header)    
            else:
                insert_replace_h_wv_with_value(name=name, datadir=args.datadir, savedir=args.savedir, header=args.header)

            