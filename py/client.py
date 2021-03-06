import sys
import socket
import os
import subprocess as sp
import json

from flask import Flask
from flask.ext.restful import reqparse, abort, Api, Resource
from flask import request, make_response
from datetime import datetime
from nltk import word_tokenize
import random
host = "holst.isi.edu"
ports = [10010, 10011, 10012]
size = 10240

root_dir = os.path.abspath(__file__ + "/../../")
fsa_path_tp = os.path.join(root_dir, "fsas/poem.fsa")
source_path_tp = os.path.join(root_dir, "fsas/source.txt")
rhyme_path_tp = os.path.join(root_dir, "fsas/rhyme.txt")
encourage_path_tp = os.path.join(root_dir, "fsas/encourage.txt")
marjan_dir = os.path.join(root_dir, "sonnet-project-for-server/")
before_path_tp = os.path.join(root_dir, "fsas/before.txt")
after_path_tp = os.path.join(root_dir, "fsas/after.txt")
ngram_path = os.path.join(root_dir,"models/5grams.txt")
curse_path = os.path.join(root_dir,"models/curse.txt")

interactive_folder_tp = os.path.join(root_dir, 'fsas_interactive/data')
interactive_folder = interactive_folder_tp

beams = [50, 200, 1000]
interactive_beams = [50, 200]
line_reverses = [1, 1]
interactive_ports = [10020, 10021]

def load_ngram():
    d = {}
    #return d
    with open(ngram_path) as f:
        for line in f:
            d[line.strip()] = 1
    print "5 grams : ", len(d)
    return d

ngram = load_ngram()

def check_plagiarism(lines,ngram):
    def check_p(line):
        d = set()
        ll = line.split()
        for i in xrange(4,len(ll)):
            phrase = " ".join(ll[i-4:i+1])
            if phrase in ngram:
                d.add(phrase)
        return d
    d = set()
    for line in lines:
        d = d.union(check_p(line))
    return d

class StatusMap:
    # 0 -> 1 -> 2 -> 3 -> 0
    # Ready -> Generating FSA -> Waiting in Queue -> Decoding by RNN -> Ready

    def __init__(self):
        self.s = {}
        self.messages = [
            "Ready", "Generating Rhyme Words/FSA", "Waiting in Queue", "Decoding by RNN"]

    def get_status(self, index):
        if not index in self.s:
            return self.messages[0]
        else:
            print index, self.s[index]
            return self.messages[self.s[index]]

    def next_status(self, index):
        if not index in self.s:
            self.s[index] = 1
        else:
            if self.s[index] == 3:
                del self.s[index]
            else:
                self.s[index] += 1

    def set_status(self, index, i):
        self.s[index] = i

    def clear_status(self, index):
        if index in self.s:
            del self.s[index]

sm = StatusMap()


def receive_all(conn):
    data = ""
    while True:
        d = conn.recv(size)
        if not d:
            break
        data += d
    return data


def post_process(lines,interactive=False):
    r = random.randint(1, 100000)
    before_path = before_path_tp + ".{}".format(r)
    after_path = after_path_tp + ".{}".format(r)

    f = open(before_path, 'w')
    nline = 0
    for line in lines:
        f.write(line.strip() + "\n")
        nline += 1
    f.close()
    
    print len(lines)
    nline = nline - 1
    if nline != 2 and nline != 4 and nline != 14:
        nline = 14
    cmd = "bash post_process.sh {} {} {}".format(before_path, after_path, nline)
    print cmd
    sp.call(cmd.split(), cwd=marjan_dir)

    f = open(after_path)
    r = ""
    iline = 0
    for line in f:
        r += line
        iline += 1
        if iline % 4 == 0:
            if not interactive:
                r += "\n"
    f.close()
    os.remove(before_path)
    os.remove(after_path)
    return r


def process_poem(poem):
    ll = poem.split()[1:-1][::-1]
    newline = "\n"
    newll = []
    for w in ll:
        if w in ['?', '!', '.', ',']:
            w += newline
        newll.append(w)

    lines = ' '.join(newll).split(newline)
    lines = [x.strip() for x in lines]
    poem_str = post_process(lines)
    poem_str = poem_str.replace("\n", "<br//>")

    return poem_str,lines


def process_results(data):
    # there is no html tags in poems
    ll = data.split("\n")
    poems = []
    times = []
    for line in ll:
        if line.startswith("<START>"):
            poems.append(process_poem(line))
        if line.startswith("Total:") or line.startswith("Forward:") or line.startswith("Expand:"):
            print sys.stderr.write(line + "\n")
            times.append(line)

    return poems, times


def process_poem_interactive(poem, line_reverse=1):
    lines = []
    if line_reverse == 1:
        ll = poem.split()[1:-1][::-1]

        newline = "\n"
        newll = []
        for w in ll:
            if w in ['?', '!', '.', ',']:
                w += newline
            newll.append(w)

        lines = ' '.join(newll).split(newline)[::-1]
        temp_lines = []
        for x in lines:
            if x != "":
                temp_lines.append(x)
        lines = temp_lines
        lines = [x.strip() for x in lines]
    else:
        ll = poem.split()[1:-1]
        newline = "\n"
        newll = []
        for w in ll:
            if w in ['?', '!', '.', ',']:
                w += newline
            newll.append(w)

        lines = ' '.join(newll).split(newline)
        temp_lines = []
        for x in lines:
            if x != "":
                temp_lines.append(x)
        lines = temp_lines
        lines = [x.strip() for x in lines]

    poem_str = post_process(lines,True)
    return poem_str.split('\n')


def process_results_interactive(data, line_reverse=1):
    ll = data.split("\n")
    poems = []
    times = []
    for line in ll:
        if line.startswith("<START>"):
            poems.append(process_poem_interactive(line, line_reverse))
        if line.startswith("Total:") or line.startswith("Forward:") or line.startswith("Expand:"):
            print sys.stderr.write(line + "\n")
            times.append(line)

    return poems, times


def read_from_stdin():
    while True:
        line = sys.stdin.readline()
        # <model-type> <k-best> <topic_phrase_or_word>
        ll = line.split()
        model_type = int(ll[0])
        k = int(ll[1])
        topic = ll[2]
        poems, times = get_poem(k, model_type, topic)
        for poem in poems:
            print poem
        for t in times:
            print t


def tokenize(words):
    words = words.strip()
    if words == "":
        return [""]
    words = word_tokenize(words)
    words = [x.lower() for x in words]
    return words

def to_table_html_2(tables):
    html = "<table class=\"table table-bordered\">"
    titles = ["Rhyme Type", "Candidates"]
    html += "<thead><tr>{}</tr></thead>".format(
        " ".join(["<th>{}</th>".format(x) for x in titles]))

    html += "<tbody>"
    for line in tables:
        temp_ll = line.split()
        ll = [temp_ll[0][:-1], " ".join(temp_ll[1:])]
        html += "<tr>{}</tr>".format(" ".join(["<td>{}</td>".format(x)
                                     for x in ll]))

    html += "</tbody>"
    html += "</table>"
    return html



def to_table_html(tables):
    html = "<table class=\"table table-bordered\">"
    titles = ["Word/phrase", "In CMU", "Scans",
              "LM", "Chosen for rhyme", "Weight"]
    html += "<thead><tr>{}</tr></thead>".format(
        " ".join(["<th>{}</th>".format(x) for x in titles]))

    html += "<tbody>"
    for line in tables:
        ll = line.split()
        html += "<tr>{}</tr>".format(" ".join(["<td>{}</td>".format(x)
                                     for x in ll]))

    html += "</tbody>"
    html += "</table>"
    return html


def get_rhyme(fn):
    f = open(fn)
    words = []
    exact_rhyme_candidate = []
    tables = []
    slant_rhymes = []

    while True:
        title = f.readline()
        if not title:
            break
        content = []
        while True:
            line = f.readline()
            if line.strip() == "":
                break
            content.append(line)

        if title.startswith("##Slant Rhyme Candidates"):
            for line in content:
                slant_rhymes.append(line.strip())
        
        
        if title.startswith('##Rhyme Words'):
            for line in content:
                words.append(line.strip())
        
        if title.startswith("##Exact Rhyme Candidates"):
            for line in content:
                exact_rhyme_candidate.append(line.strip())
        
        if title.startswith("##Rhyme info"):
            for line in content:
                tables.append(line.strip())
        
    rhyme_table_html = to_table_html_2(exact_rhyme_candidate)
    table_html = to_table_html(tables)
    return words, (table_html,rhyme_table_html,slant_rhymes)


def process_topic(topic):
    topic = topic.lower()
    for i in xrange(len(topic)):
        if not topic[i] == "_":
            if not topic[i].isalpha():
                tmp = topic[i]
                topic = topic.replace(tmp,"_")
    topic = '{}'.format(" ".join(topic.split("_")))
    return topic


def get_poem_compare(topic, c1, c2, index=0):
    # return times, poems, rhyme_words, rhyme_info_html.

    r = random.randint(1, 100000)

    def rf(path):
        return '{}.{}'.format(path, r)

    fsa_path = rf(fsa_path_tp)
    source_path = rf(source_path_tp)
    rhyme_path = rf(rhyme_path_tp)

    cmd = ["bash", "run.sh", topic, fsa_path, source_path, rhyme_path]
    print cmd
    sys.stderr.write("generating fsa!\n")
    sm.next_status(index)

    sp.call(cmd, cwd=marjan_dir)

    sys.stderr.write("fsa generated! start decoding!\n")

    def _t_(model_type):

        sm.set_status(index, 2)
        port = ports[model_type]
        data = ""

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        s.connect((host, port))
        message = s.recv(1024)
        print host, port, message
        assert(message == 'Accept')
        sm.set_status(index, 3)
        k = 1
        s.send("{} {} {}\n".format(k, source_path, fsa_path))
        data = receive_all(s)

        s.close()

        poems, times = process_results(data)
        rhyme_words, table_html = get_rhyme(rhyme_path)
        return times, poems, rhyme_words, table_html

    r1 = _t_(c1['model'])
    r2 = _t_(c2['model'])

    os.remove(fsa_path)
    os.remove(source_path)
    os.remove(rhyme_path)
    sm.next_status(index)

    return r1, r2


def get_poem(k, model_type, topic, index=0, check=False, nline = None, no_fsa=False, style = None, withRhymeTable=False):
    # return times, poems, rhyme_words, rhyme_info_html.

    r = random.randint(1, 100000)
    if index!=0:
        r = index

    def rf(path):
        return '{}.{}'.format(path, r)

    fsa_path = rf(fsa_path_tp)
    source_path = rf(source_path_tp)
    rhyme_path = rf(rhyme_path_tp)
    encourage_path = rf(encourage_path_tp)

    topic = process_topic(topic)

    if model_type == -1:  # Rhyme words only
        cmd = ["bash", "run_rhyme.sh", topic, rhyme_path]
        print cmd
        sys.stderr.write("generating rhyme!\n")

        sm.next_status(index)

        print cmd
        sp.call(cmd, cwd=marjan_dir)

        rhyme_words, table_html = get_rhyme(rhyme_path)

        sm.clear_status(index)
        os.remove(rhyme_path)

        return [], [], rhyme_words, table_html, rhyme_table_html
    
    if not no_fsa:
        cmd = ["bash", "run.sh", topic, fsa_path, source_path, rhyme_path, encourage_path]
        if nline != None:
            if withRhymeTable:
                cmd = ["bash", "run-different-line-numbers.sh", topic, fsa_path, source_path, rhyme_path, encourage_path, str(nline)]
            else:
                cmd = ["bash", "run-different-line-numbers.sh", topic, fsa_path, source_path, encourage_path, str(nline)]
        print cmd
        sys.stderr.write("generating fsa!\n")
        sm.next_status(index)

        sp.call(cmd, cwd=marjan_dir)

        sys.stderr.write("fsa generated! start decoding!\n")
    else:
        sm.next_status(index)

    sm.next_status(index)

    port = ports[model_type]
    data = ""


    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if model_type <= 2:  # translation
        message = "k:{} source_file:{} fsa_file:{}".format(k,source_path,fsa_path)
        #s.send("{} {} {} {} {}\n".format(k, source_path, fsa_path, encourage_path, 1.0))
        
        encourage_files = [encourage_path]
        encourage_weights = [1.0]
        args = style
        if args != None:
            print "Here"
            if "encourage_words" in args:
                encourage_words = args['encourage_words'].lower().split()
                if len(encourage_words) > 0:
                    user_encourage_path = rf(encourage_path_tp+".user")
                    f =  open(user_encourage_path,'w')
                    for word in encourage_words:
                        f.write(word+"\n")
                    f.flush()
                    f.close()
                    encourage_files.append(user_encourage_path)
                    encourage_weights.append(float(args['enc_weight']))
                    
            if "disencourage_words" in args:
                disencourage_words = args['disencourage_words'].lower().split()
                if len(disencourage_words) > 0:
                    user_disencourage_path = rf(encourage_path_tp+".dis.user")
                    f =  open(user_disencourage_path,'w')
                    for word in disencourage_words:
                        f.write(word+"\n")
                    f.flush()
                    f.close()
                    encourage_files.append(user_disencourage_path)
                    encourage_weights.append(-float(args['enc_weight']))
                
            if "cword" in args and args["cword"]:
                cword = float(args['cword'])
                encourage_files.append(curse_path)
                encourage_weights.append(cword)
                
            message += " encourage_list_files:{} encourage_weights:{}".format(",".join(encourage_files), ",".join([str(x) for x in encourage_weights]))
                
            if "reps" in args and args["reps"]:
                reps = float(args['reps'])
                message += " repetition:{}".format(reps)
            if "allit" in args and args["allit"]:
                allit = float(args['allit'])
                message += " alliteration:{}".format(allit)
            if "slant" in args and args["slant"]:
                slant = float(args['slant'])
                # not support now .. 
            if "wordlen" in args and args["wordlen"]:
                wordlen = float(args['wordlen'])
                message += " wordlen:{}".format(wordlen)


        s.connect((host, port))
        message_old = s.recv(1024)
        print host, port, message_old
        assert(message_old == 'Accept')
        sm.next_status(index)

        sys.stderr.write(message+'\n')
        s.send(message+"\n")
        data = receive_all(s)
    else:
        s.connect((host, port))
        message = s.recv(1024)
        print host, port, message
        assert(message == 'Accept')
        sm.next_status(index)
        s.send("{} {}\n".format(k, fsa_path))
        data = receive_all(s)

    s.close()

    poems, times = process_results(data)
    if withRhymeTable:
        rhyme_words, table_html = get_rhyme(rhyme_path)
    else:
        rhyme_words, table_html = "",["","",""]
    sm.next_status(index)

    #os.remove(fsa_path)
    #os.remove(source_path)
    #os.remove(rhyme_path)

    new_poems = []
    lines = []
    for p,l in poems:
        new_poems.append(p)
        lines.append(l)

    if check:
        return times, new_poems, rhyme_words, table_html, lines
    else:
        return times, new_poems, rhyme_words, table_html

def log_it(beamsize,topic,poems,times):
    flog = open(os.path.join(root_dir, 'py/log.txt'), 'a')
    flog.write("Time: " + datetime.now().isoformat() + "\n")
    flog.write("Beam_size: {}\nTopic: {}\n".format(beamsize, topic))
    flog.write('\n'.join(times) + "\n")
    flog.write("----------------------\n")
    flog.write("\n".join([x.replace("<br//>", '\n') for x in poems]) + "\n")
    flog.write('\n')
    flog.close()

## app and api

app = Flask(__name__)
api = Api(app)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add(
        'Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response


class Status(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id')
        args = parser.parse_args()
        index = 'default'
        if "id" in args:
            index = args['id']

        return make_response(sm.get_status(index))

# need to reserve, daniel is using this one
class POEM(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('k')
        parser.add_argument('model')
        parser.add_argument('topic')
        parser.add_argument('id')

        args = parser.parse_args()
        k = int(args['k'])
        model_type = int(args['model'])
        topic = args['topic']
        index = 'default'
        if "id" in args:
            index = args['id']

        assert(k > 0)
        assert(model_type == 0 or model_type ==
               1 or model_type == 2 or model_type == -1)
        assert(len(topic) > 0)

        print model_type, k, topic
        times, poems, rhyme_words, table_html = get_poem(
            k, model_type, topic, index)

        # log it
        if model_type >= 0:
            log_it(beams[model_type],topic,poems,times)

        poem_str = "<br//><br//>".join(poems)

        rhyme_words_html = "<br//>".join(rhyme_words)

        config_str = ""

        f = open(os.path.join(root_dir, 'py/config.txt'))
        for line in f:
            config_str += line.strip() + "<br//>"
        f.close()

        d = {}
        d['poem'] = poem_str
        d['config'] = config_str
        d['rhyme_words'] = rhyme_words_html
        d['rhyme_info'] = table_html[0]
        d['exact_rhyme_candidates'] = table_html[1]
        json_str = json.dumps(d, ensure_ascii=False)
        r = make_response(json_str)

        return r


################### Interactive ####################

class Rhyme(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('topic')
        parser.add_argument('id')
        parser.add_argument('nline')

        args = parser.parse_args()
        topic = args['topic']
        index = 'default'
        nline = None
        if "id" in args:
            index = args['id']
        if "nline" in args:
            nline = int(args['nline'])

        times, poems, rhyme_words, table_html = get_rhyme_interactive(
            topic, index, nline = nline)
        d = {}
        d['rhyme_words'] = rhyme_words

        json_str = json.dumps(d, ensure_ascii=False)
        r = make_response(json_str)
        sm.clear_status(index)

        return r


class Confirm(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('words')
        parser.add_argument('id')

        args = parser.parse_args()
        words_json = args['words']
        index = 'default'
        if "id" in args:
            index = args['id']

        r = make_response("Got It")
        sm.clear_status(index)

        return r


def mymkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)


def get_rhyme_interactive(topic, index, line_reverse=1, nline = None):
    def rf(path, r):
        return '{}.{}'.format(path, r)

    interactive_folder = rf(interactive_folder_tp, index)
    mymkdir(interactive_folder)
    source_path = os.path.join(interactive_folder, "source.txt")
    rhyme_path = os.path.join(interactive_folder, "rhyme.txt")
    encourage_path = os.path.join(interactive_folder, "encourage.txt")

    topic = process_topic(topic)

    cmd = ["bash", "run-interactive.sh", topic,
           str(line_reverse), interactive_folder, source_path, rhyme_path]
    
    if nline == 14 or nline == 4 or nline == 2:
        cmd = ["bash", "run-interactive-different-line-numbers.sh", topic,
               str(line_reverse), interactive_folder, source_path, rhyme_path, encourage_path, str(nline)]

    sys.stderr.write("generating rhyme!\n")

    sm.next_status(index)

    print cmd
    sp.call(cmd, cwd=marjan_dir)

    rhyme_words, table_html = get_rhyme(rhyme_path)

    sm.clear_status(index)

    return [], [], rhyme_words, table_html


def send_receive(host, port, ins):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    message = s.recv(1024)
    print host, port, message
    assert(message == 'Accept')
    s.send(ins)
    data = receive_all(s)
    s.close()
    return data


def get_poem_interactive(model_type, action, index, iline, words=[], line_reverse=1):
    # return times, poems, rhyme_words, rhyme_info_html.
    def rf(path, r):
        return '{}.{}'.format(path, r)

    interactive_folder = rf(interactive_folder_tp, index)
    mymkdir(interactive_folder)
    source_path = os.path.join(interactive_folder, "source.txt")
    rhyme_path = os.path.join(interactive_folder, "rhyme.txt")

    port = interactive_ports[model_type]
    data = ""

    if iline == 1:  # the first line
        ins = "source {}\n".format(source_path)
        print ins
        data = send_receive(host, port, ins)

    sm.set_status(index, 3)

    ins = "default"
    if action == "fsa":
        fsa_path = os.path.join(
            interactive_folder, "fsa_start-{}".format(iline - 1))
        ins = "fsa {}\n".format(fsa_path)
    elif action == "fsaline":
        fsa_path = os.path.join(interactive_folder, "fsa{}".format(iline - 1))
        ins = "fsaline {}\n".format(fsa_path)
    elif action == "words":
        words_str = " ".join(words)
        ins = "words {}\n".format(words_str)

    print ins
    data = send_receive(host, port, ins)

    poems, times = process_results_interactive(data, line_reverse)
    rhyme_words, table_html = get_rhyme(rhyme_path)
    sm.clear_status(index)

    return times, poems, rhyme_words, table_html


class POEMI(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('model')
        parser.add_argument('action')
        parser.add_argument('line')
        parser.add_argument('words')
        parser.add_argument('id')

        args = parser.parse_args()

        model_type = int(args['model'])

        action = args['action']
        assert(action == "words" or action == "fsa" or action == "fsaline")

        index = 'default'
        if "id" in args:
            index = args['id']

        iline = int(args['line'])
        assert(iline <= 14 and iline >= 1)

        words = args['words']
        words = tokenize(words)

        line_reverse = 1
        if line_reverse == 1:
            words = words[::-1]

        if action == "words" and len(words) == 1 and words[0] == "":
            words = ["<UNK>"]

        print "poem_interactive", model_type, action, iline, words, index
        times, poems, rhyme_words, table_html = get_poem_interactive(
            model_type, action, index, iline, words)

        rhyme_words_html = "<br//>".join(rhyme_words)

        config_str = ""

        f = open(os.path.join(root_dir, 'py/config.txt'))
        for line in f:
            config_str += line.strip() + "<br//>"
        f.close()

        if len(poems) > 0:
            poems = poems[0]

        d = {}
        d['poem'] = poems
        d['config'] = config_str
        d['rhyme_words'] = rhyme_words_html
        d['rhyme_info'] = table_html
        json_str = json.dumps(d, ensure_ascii=False)
        r = make_response(json_str)

        return r

def load_random_topic():
    topics = []
    f = open('random_topic.txt')
    for line in f:
        topics.append(line.strip())
    r = random.randint(0, len(topics) - 1)
    f.close()
    return process_topic(topics[r])


def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w


def load_compare(fn):
    f = open(fn)
    line = f.readline()

    def get_config(line):
        c = [x.split("=") for x in line.split()]
        poem1 = {}
        for k, v in c:
            poem1[k] = int(v)
        return poem1
    c1 = get_config(line)
    line = f.readline()
    c2 = get_config(line)
    f.close()
    return (c1, c2)


def load_random_config():
    f = open(os.path.join(root_dir, 'compare/random_compare.txt'))
    choices = []
    for line in f:
        ll = line.split()
        choices.append((ll[0], float(ll[1])))
    config_file = weighted_choice(choices)
    config_path = os.path.join(root_dir, "compare/" + config_file)
    f.close()
    c1, c2 = load_compare(config_path)
    return c1, c2, config_file


class POEM_compare(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('topic')
        parser.add_argument('id')

        args = parser.parse_args()

        topic = args['topic']
        if topic == "-1":
            # choose from random topic
            topic = load_random_topic()

        index = 'default'
        if "id" in args:
            index = args['id']

        c1, c2, config_file = load_random_config()

        print "poem_compare", index, topic, c1, c2, config_file
        r1, r2 = get_poem_compare(topic, c1, c2, index)

        


        pome1 = ""
        poem2 = ""
        if len(r1[1]) > 0:
            poem1 = r1[1][0][0]
        if len(r2[1]) > 0:
            poem2 = r2[1][0][0]


        log_it(beams[c1['model']], topic, [poem1], r1[0])
        log_it(beams[c2['model']], topic, [poem2], r2[0])


        reverse = random.randint(0, 1)

        print reverse, poem1

        if reverse == 1:
            poem1, poem2 = poem2, poem1

        d = {}
        d['poem1'] = poem1
        d['poem2'] = poem2
        d['reverse'] = reverse
        d['config_file'] = config_file
        d['topic'] = topic
        json_str = json.dumps(d, ensure_ascii=False)
        r = make_response(json_str)

        return r


class POEM_submit(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('topic')
        parser.add_argument('result')
        parser.add_argument('poem1')
        parser.add_argument('poem2')
        parser.add_argument('config_file')

        args = parser.parse_args()
        d = args
        d['time'] = datetime.now().isoformat()
        json_str = json.dumps(d, ensure_ascii=False)
        json_str.replace('\n', "\\n")
        f = open(os.path.join(root_dir, 'py/compare_result.txt'), 'a')
        f.write(json_str + "\n")
        f.close()

        r = make_response("Done")

        return r

class POEM_check(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('k')
        parser.add_argument('model')
        parser.add_argument('topic')
        parser.add_argument('nline')
        parser.add_argument('id')
        # style
        # do not support phrase now;
        parser.add_argument("encourage_words")
        parser.add_argument("disencourage_words")
        parser.add_argument("enc_weight")
        parser.add_argument('cword')
        parser.add_argument('reps')
        parser.add_argument('allit')
        parser.add_argument('slant')
        parser.add_argument('wordlen')
        
        # no_fsa
        parser.add_argument('no_fsa')
        

        args = parser.parse_args()
        print args
        k = int(args['k'])
        model_type = int(args['model'])
        topic = args['topic']
        index = 'default'
        if "id" in args:
            index = args['id']

        nline = 14
        if "id" in args:
            index = args['id']
        if "nline" in args:
            nline = int(args['nline'])        
        if not (nline == 2 or nline == 4 or nline == 14):
            nline = 14

        # no_fsa
        no_fsa = False
        if "no_fsa" in args and args['no_fsa'] == "1":
            no_fsa = True
        

        assert(k > 0)
        assert(model_type == 0 or model_type ==
               1 or model_type == 2 or model_type == -1)
        assert(len(topic) > 0)

        print model_type, k, topic
        times, poems, rhyme_words, table_html,lines = get_poem(
            k, model_type, topic, index, check=True, nline = nline, no_fsa = no_fsa, style = args)
        
        
        # log it
        if model_type >= 0:
            log_it(beams[model_type],topic,poems,times)

        phrases = []
        if len(lines) > 0:
            phrases = list(check_plagiarism(lines[0],ngram))
        phrase_str = "<br//>".join(phrases)

        poem_str = "<br//><br//>".join(poems)

        rhyme_words_html = "<br//>".join(rhyme_words)

        config_str = ""

        f = open(os.path.join(root_dir, 'py/config.txt'))
        for line in f:
            config_str += line.strip() + "<br//>"
        f.close()

        d = {}
        d['poem'] = poem_str
        d['config'] = config_str
        d['rhyme_words'] = rhyme_words_html
        d['rhyme_info'] = table_html[0]
        d['exact_rhyme_candidates'] = table_html[1]
        d['slant_rhyme_candidates'] = "<br//>".join(table_html[2])
        d['pc'] = phrase_str
        json_str = json.dumps(d, ensure_ascii=False)
        r = make_response(json_str)

        return r

class POEM_short(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('k')
        parser.add_argument('model')
        parser.add_argument('topic')
        parser.add_argument('nline')
        parser.add_argument('id')

        args = parser.parse_args()
        k = int(args['k'])
        model_type = int(args['model'])
        topic = args['topic']
        index = 'default'
        nline = 2
        if "id" in args:
            index = args['id']
        if "nline" in args:
            nline = int(args['nline'])        
        if not (nline == 2 or nline == 4 or nline == 14):
            nline = 2

        assert(k > 0)
        assert(model_type == 0 or model_type ==
               1 or model_type == 2 or model_type == -1)
        assert(len(topic) > 0)


        print model_type, k, topic, nline
        times, poems, rhyme_words, table_html = get_poem(
            k, model_type, topic, index, check=False, nline = nline)
        
        
        # log it
        if model_type >= 0:
            log_it(beams[model_type],topic,poems,times)

        lines = []
        phrases = []
        if len(lines) > 0:
            phrases = list(check_plagiarism(lines[0],ngram))
        phrase_str = "<br//>".join(phrases)

        poem_str = "<br//><br//>".join(poems)

        rhyme_words_html = "<br//>".join(rhyme_words)

        config_str = ""

        f = open(os.path.join(root_dir, 'py/config.txt'))
        for line in f:
            config_str += line.strip() + "<br//>"
        f.close()

        d = {}
        d['poem'] = poem_str
        d['config'] = config_str
        d['rhyme_words'] = rhyme_words_html
        d['rhyme_info'] = table_html
        d['pc'] = phrase_str
        json_str = json.dumps(d, ensure_ascii=False)
        r = make_response(json_str)

        return r



# add endpoint
api.add_resource(POEM, '/api/poem')
api.add_resource(Rhyme, "/api/rhyme")
api.add_resource(Confirm, "/api/confirm")
api.add_resource(Status, '/api/poem_status')
api.add_resource(POEMI, '/api/poem_interactive')
api.add_resource(POEM_submit, '/api/poem_submit')
api.add_resource(POEM_compare, '/api/poem_compare')
api.add_resource(POEM_check, '/api/poem_check')
api.add_resource(POEM_short, '/api/poem_short')


if __name__ == '__main__':
    # read_from_stdin()
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.run(threaded=True, debug=True, host='cage.isi.edu', port=8080)
