1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70
71
72
73
74
75
76
77
78
79
80
81
82
83
84
85
86
87
88
89
90
91
92
93
94
95
96
import json
import random
from collections import defaultdict
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
from core import engine as en
from core import storage as db
from urllib.parse import quote_plus
import os
import time

def google_url(topic, exam, grade):
    return "https://www.google.com/search?q=" + quote_plus(f"{exam} {grade} {topic} practice questions")

def setting(name, default=""):
    try:
        return str(st.secrets.get(name, os.environ.get(name, default)))
    except Exception:
        return os.environ.get(name, default)

st.set_page_config(page_title='StudyLens AI 2.0',page_icon='🎓',layout='wide')
db.init()
st.title('🎓 StudyLens AI 2.0')
st.caption('Diagnose · Plan · Practise · Improve — hosted custom-topic AI')

for name,default in {'quiz':[], 'results':None,'quiz_key':'','report':'','cards_from_resource':[], 'source_text':''}.items():
    if name not in st.session_state:st.session_state[name]=default

with st.sidebar:
    st.header('Your preparation')
    demo_id=st.text_input('Demo identifier (not a password)','Exhibition Guest').strip() or 'Exhibition Guest'
    exam=st.selectbox('Preparation domain',en.EXAMS,index=en.EXAMS.index('ISC Boards'))
    if exam=='Other / Custom':exam=st.text_input('Specify examination','School examination')
    grade=st.selectbox('Level',['Class 8','Class 9','Class 10','Class 11','Class 12','Graduation','Other'],index=3)
    st.info('Cloud AI generates custom-topic questions; the curated bank needs no API key.')
    section=st.radio('Navigate',['🏠 Overview','📝 Diagnostic Test','📊 My Diagnostics','🗓️ Study Planner','🃏 Flashcards','✅ Revision Tracker','💬 Concept Coach','🧪 Same-Score Lab','📚 Source Material'])

st.markdown('''<style>.block-container{max-width:1250px}.stButton button{border-radius:9px}</style>''',unsafe_allow_html=True)

history=db.attempts(demo_id)
all_diagnostics=en.diagnostic(history)
known_topics=list(dict.fromkeys([x['topic'] for x in history]))

# Material is session-scoped; no uploaded book content saved in the SQLite database.
def extract_upload(upload):
    suffix=upload.name.lower()
    if suffix.endswith('.txt') or suffix.endswith('.md'):
        return upload.getvalue().decode('utf-8',errors='replace')
    if suffix.endswith('.pdf'):
        from pypdf import PdfReader
        reader=PdfReader(BytesIO(upload.getvalue()))
        return '\n'.join((p.extract_text() or '') for p in reader.pages[:35])
    if suffix.endswith('.docx'):
        from docx import Document
        return '\n'.join(p.text for p in Document(BytesIO(upload.getvalue())).paragraphs)
    return ''

if section=='🏠 Overview':
    st.subheader('A personalised preparation workbench')
    st.write('Choose your exam, test specific topics, record confidence, and use the four-quadrant diagnostic to decide what to revise next.')
    c1,c2,c3=st.columns(3)
    c1.metric('Questions attempted',len(history))
    c2.metric('Overall accuracy',f"{100*sum(x['correct'] for x in history)/len(history):.0f}%" if history else '—')
    c3.metric('Tracked concepts',len(all_diagnostics))
    st.info('Start with Diagnostic Test. For an instant exhibition demonstration use Same-Score Lab.')
    st.write('**About this demo:** built-in question bank and rule-based study tools work on Streamlit Cloud. Cloud AI generates custom-topic quizzes using a privately configured provider key; Gemini powers custom-topic generation. The selected exam is a preparation label; this prototype does not implement every official exam format.')

elif section=='📚 Source Material':
    st.subheader('Your notes and learning resources')
    uploads=st.file_uploader('Upload PDF, DOCX or text (extractable text only)',type=['pdf','docx','txt','md'],accept_multiple_files=True)
    pasted=st.text_area('Or paste your notes',height=180)
    if st.button('Extract material'):
        combined=pasted+'\n'+'\n'.join(extract_upload(f) for f in (uploads or []))
        st.session_state.source_text=combined[:60000]
        st.success(f'Extracted {len(st.session_state.source_text):,} characters into this browser session.')
    text=st.session_state.source_text
    if text:
        with st.expander('Preview extracted text'):st.text(text[:4000])
        st.caption('This can create source-grounded recall cards without AI. Loaded notes can guide Cloud AI assessments. Scanned PDFs and video/audio lectures need transcripts/OCR first.')
        snippets=en.extract_candidates(text)
        st.write(f'{len(snippets)} candidate source passages found.')
        if st.button('Create source recall flashcards'):
            n=0
            for snippet in snippets[:12]:
                db.card_add(demo_id,'Uploaded material','Recall and explain this passage:',snippet)
                n+=1
            st.success(f'Added {n} source-excerpt recall cards.')

elif section=='📝 Diagnostic Test':
    st.subheader('Start a diagnostic assessment')
    subjects=sorted(set(x[0] for x in en.SEEDS))
    subject=st.selectbox('Subject',subjects+['Custom subject'],index=0)
    if subject=='Custom subject':
