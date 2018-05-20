import time, nltk, spacy, os, csv, nsettings
from nltk import word_tokenize
from nltk.corpus import wordnet
from spacy.symbols import * 
#load word vectors for finding similar phrases
spcynlp = spacy.load('en_core_web_sm',disable=['parser', 'tagger']) # must "spacy download en_core_web_sm" first

#nltk.download('popular')
#load punkt data on OSX
#sent_detector = nltk.data.load('/usr/local/share/nltk_data/tokenizers/punkt/english.pickle')

#load punkt data on linux # requires ntlk.download
sent_detector = nltk.data.load(os.environ["HOME"]+'/nltk_data/tokenizers/punkt/english.pickle')

def chunks(listobj, chunksize):
    '''takes a list, yields it as a series of chunksize chunks'''
    for i in range(0, len(listobj), chunksize):
        yield listobj[i:i + chunksize]

def check_vectors(s2):
    '''check if phrases are similar in meaning'''
    VCOUNT = 0
    slist = s2.split(' ')
    p1 = spcynlp(s2)
    for phrase in nsettings.GDPRVECTORS.split(','):
        #compare our GDPR phrase to each sentence of paragraph
        #if GDPR phrase matches a sentence, flag paragraph
        p2=spcynlp(phrase)
        VCOUNT+=1
        vecsim = 0
        vecsim = p1.similarity(p2)
        if vecsim > 0.8:
            return True
    return False

#load admin dictionary overrides for on-site dictionary (i.e. when you click highlighted phrase)
admindict = dict()
with open(os.getcwd()+'/static/admin.dict.txt') as f:
    temp = f.readlines()
    for line in temp:
        if line.strip():
            l = line.split(',')
            admindict[l[0]] = ', '.join(l[1:])

def highlight(username,mode='keyword',keywords={},uimode='advanced',cboxes=''):
    '''return html-tagged corpus for highlighting by css/js
    will act according to mode (keyword or profile) passed to it'''
    cboxes = [int(n) for n in cboxes.split(',') if n] if cboxes else list()
    print('pcboxbes:',cboxes)
    time1 = time.time()
    with open('uploads/%s.corpusfile.txt' %username,'r') as f:
        sentences = sent_detector.tokenize(f.read().strip())
        #f.seek(0); document = f.readlines(); sentences = list()
        #for s in document: sentences += sent_detector.tokenize(s)

    #assign a color to a list of keywords, to highlight that sentence
    KEYWORDS = dict()
    if mode == 'keyword':
        if uimode=='simple':
            grouprange = [1]
        else:
            grouprange = [1,2,3,4,5,6]
        for group in grouprange:
            KEYWORDS[tuple([k.strip() for k in keywords[group].split(',')])] = group
        #GDPR:
        gdprwords = nsettings.GDPRWORDS
        KEYWORDS[tuple([k.strip() for k in gdprwords.split(',')])] = 7
    '''iterate through sentences and keywords, find any sentence containing a keyword'''
    result = ''
    line_no = -1
    for s1 in sentences:
        for s in s1.split('\n'):
            vecfound = check_vectors(s) if s and nsettings.VECTORS_ENABLED else False
        
            #check GDPR word vectors
            line_no+=1
            s2 = s.strip().lower()
            for group in KEYWORDS.keys():
                #FLAG means we found a keyword
                FLAG = False
                for snippet in group:
                    #where "snippet" is our keyword and s is the line in the document. #s2 is just s.lower().strip()
                    definition = ''
                    tokenized = word_tokenize(s2)
                    #            keyword                            keyphrase 
                    if (snippet in tokenized or (' ' in snippet and snippet in s2)) and snippet:
                        if snippet in admindict:
                            definition = admindict[snippet]
                        else:
                            try:
                                #try to find in wordnet
                                definition = wordnet.synsets(snippet)[0].definition()
                            except Exception as e:
                                #notfound
                                definition = 'not in dictionary'
                        flagoffset = (len(s)//64) + 2
                        #the GDPR flag to display on the right of page
                        gdprflag = '''<div style="margin-top:-%drem"; class="gdpr-flag">\
                                        <div class="gdpr-flagarrow"></div>\
                                        <div class="gdpr-flagtext">GDPR</div>\
                                    </div>''' %(flagoffset)

                        #only show GDPR flag if found gdpr keyword or vector match.
                        #TODO: gdpr is a hidden group 7, user only gets 6 keyword groups
                        #TODO: if changing this to allow more user keyword groups, change 7 ...
                        gnum = KEYWORDS[group]
                        if not vecfound and gnum!=7:
                            gdprflag=''
                        
                        result += '''<div style="display:inline-block; float:left; margin-left:-5ex; padding-right:2ex; transform:scale(1.75);"\
                                        class="usercheckbox"><input type="checkbox" name="line-%d" class="pcbox" %s autocomplete=off></div>\
                                    <span class="color group%s">\
                                    <span class="word">keyword: (%s)</span>\
                                    <span class="definition">%s</span>%s</span>
                                    %s''' %(line_no,'checked' if line_no in cboxes else '',KEYWORDS[group],snippet,definition,s,gdprflag)
                        FLAG = True
                        break
                if FLAG: break
            if not FLAG: 
                result += s+"<br>"
        result+="<br>"

    #return html markup
    return result
