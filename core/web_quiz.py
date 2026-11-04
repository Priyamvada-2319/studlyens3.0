"""Public-reference quiz builder. No API key; these are template questions, not LLM output."""
import random
import re
from urllib.parse import quote

import requests

API = 'https://en.wikipedia.org/w/api.php'
HEADERS = {'User-Agent': 'StudyLensEducationPrototype/0.2 (educational demonstration; contact: example@example.com)'}


def google_url(topic, exam, level):
    return 'https://www.google.com/search?q=' + quote(f'{topic} {exam} {level} study guide')


def _fetch(query):
    search = requests.get(API, params={
        'action': 'query', 'list': 'search', 'srsearch': query,
        'srlimit': 20, 'format': 'json', 'utf8': 1,
    }, headers=HEADERS, timeout=12)
    search.raise_for_status()
    hits = search.json().get('query', {}).get('search', [])
    titles = [r['title'] for r in hits if r.get('title') and ':' not in r['title']][:16]
    if not titles:
        return []
    pages_response = requests.get(API, params={
        'action': 'query', 'prop': 'extracts', 'explaintext': 1,
        'exintro': 1, 'exchars': 2200, 'titles': '|'.join(titles),
        'format': 'json', 'redirects': 1,
    }, headers=HEADERS, timeout=15)
    pages_response.raise_for_status()
    pages = pages_response.json().get('query', {}).get('pages', {})
    by_title = {p.get('title',''):p for p in pages.values()}
    output = []
    for title in titles:
        p = by_title.get(title)
        if not p: continue
        extract = re.sub(r'\s+', ' ', p.get('extract','')).strip()
        if len(extract) < 90: continue
        output.append({'title': title, 'extract': extract,
                       'url': 'https://en.wikipedia.org/wiki/' + quote(title.replace(' ', '_'))})
    return output


def _description(item, difficulty):
    sents = re.split(r'(?<=[.!?])\s+', item['extract'])
    sents = [s.strip() for s in sents if 70 <= len(s.strip()) <= 420]
    if not sents: return ''
    if difficulty == 'Easy': chosen = sents[0]
    elif difficulty == 'Intermediate': chosen = sents[min(1, len(sents)-1)]
    else: chosen = sents[min(2, len(sents)-1)]
    title = item['title']
    # Remove the answer from the description; skip if that leaves a poor clue.
    chosen = re.sub(re.escape(title), 'this subject', chosen, flags=re.IGNORECASE)
    for token in re.split(r'\s*\([^)]*\)', title):
        if len(token)>5: chosen = re.sub(re.escape(token), 'this subject', chosen, flags=re.IGNORECASE)
    if len(chosen)<60: return ''
    return chosen


def generate_reference_quiz(subject, topic, difficulty, count=5, exam='', grade=''):
    """Returns at least count grounded identification MCQs or raises ValueError."""
    if count < 5: count = 5
    if count > 12: count = 12
    query = f'{topic} {subject}' if subject and subject.lower() != topic.lower() else topic
    items = _fetch(query)
    if len(items)<4:
        raise ValueError('Not enough public reference pages for this topic. Try a broader topic.')
    random.shuffle(items)
    cards = []
    names = list(dict.fromkeys(x['title'] for x in items))
    for item in items:
        desc = _description(item, difficulty)
        if not desc: continue
        other = [x for x in names if x != item['title']]
        if len(other)<3: continue
        answer = item['title']
        options = random.sample(other, 3) + [answer]
        random.shuffle(options)
        cards.append({
            'id': 'wiki-' + str(random.getrandbits(64)),
            'subject': subject or 'General', 'topic': topic,
            'difficulty': difficulty,
            'question': 'Which of the following topics best matches this reference description?\n\n' + desc,
            'options': options, 'answer': answer,
            'explanation': f'Reference: {item["url"]}\n\n{item["extract"][:330]}',
            'source': 'Wikipedia reference-based (template-generated)',
        })
        if len(cards) >= count: break
    if len(cards) < 5:
        raise ValueError('Fewer than five reliable source-based questions could be prepared. Try a broader topic.')
    return cards
