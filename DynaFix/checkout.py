"""
DATA PROCESS SCRIPTS
FOR DEFECTS4J V2.0
"""
import os


def get_repos(root_dir, proj_list, id_list):
    repos_dir = root_dir + 'defects4j_buggy/'
    for i in range(len(proj_list)):
        project = proj_list[i]
        for j in id_list[i]:
            unique_id = project + '_' + str(j)
            try:
                print("in processing: " + project + '_' + str(j))
                cmd = 'defects4j checkout -p ' + project + ' -v ' + str(j) + 'b -w ' + repos_dir + unique_id + '_buggy'
                os.system(cmd)
                # print(cmd)
            except (RuntimeError, TypeError, NameError, FileNotFoundError) as e:
                print(e)


root_dir = os.getcwd() + '/'
proj_list = [
    'Chart',
    'Math',
    'Lang',
    'Cli',
    'Closure',
    'Codec',
    'Mockito',
    'Jsoup',
    'JacksonDatabind',
    'JacksonCore',
    'Compress',
    'Collections',
    'Time',
    'JacksonXml',
    'Gson',
    'Csv',
    'JxPath'
]
id_range = [
    '1-25',
    '1-105',
    '1-64',
    '2-40',
    '1-170',
    '2-18',
    '1-37',
    '2-93',
    '2-112',
    '2-26',
    '2-47',
    '26-28',
    '1-27',
    '2-6',
    '2-18',
    '2-16',
    '2-22',
]
id_list = []
for i in range(len(id_range)):
    rangeStart = id_range[i].split('-')[0]
    rangeEnd = id_range[i].split('-')[1]
    id_list.append(range(int(rangeStart), int(rangeEnd) + 1))

get_repos(root_dir, proj_list, id_list)
