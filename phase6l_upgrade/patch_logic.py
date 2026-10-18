import re

MARKER = 'exploreanywhere-phase6l-visitor-ux-v1'


def once(s,old,new,filename):
    c=s.count(old)
    if c != 1:
        raise ValueError(f'{filename}: expected unique anchor (found {c}): {old[:110]!r}')
    return s.replace(old,new,1)


def patch_modes(s):
    n='templates/places/_discovery_modes.html'
    s=once(s, '<p class="ea6f-explain">All Places: hobby relevance, filters, and destinations. Near Me: verified businesses, real place details, and optional distance from GPS or a landmark. Map View: published destinations with usable coordinates.</p>', '<p class="ea6f-explain">Explore verified Kabankalan places. Search for an interest, browse nearby listings, or switch to the map.</p>',n)
    s=once(s,'  <div class="ea6f-categories" aria-label="Find a type of place">','  {% if active_discovery_mode != "nearby" %}\n  <div class="ea6f-categories" aria-label="Find a type of place">',n)
    s=once(s,'  </div>\n</nav>', '  </div>\n  {% endif %}\n</nav>',n)
    s=once(s,'<style>','<style>\n/* '+MARKER+' */',n)
    return s


def patch_carousel(s):
    n='templates/places/attraction_carousel.html'
    css='''
/* exploreanywhere-phase6l-visitor-ux-v1: search first, filters optional */
.ea6l-search-row{display:flex;align-items:end;gap:12px;min-width:0}
.ea6l-search-row .ea-tool-field{flex:1 1 300px;min-width:0}
.ea6l-submit{min-height:46px;flex:0 0 auto;white-space:nowrap;padding:10px 20px;border-radius:11px;border:1px solid #0757d8;background:#0757d8;color:#fff;font:inherit;font-size:14px;font-weight:800;cursor:pointer}
.ea6l-submit:hover{background:#064ab3}
.ea6l-submit:focus-visible{outline:3px solid #82b5ff;outline-offset:2px}
.ea6l-filters{margin-top:13px;border:1px solid #dce7f5;background:#f9fbff;border-radius:12px;padding:0 13px}
.ea6l-filters summary{padding:12px 0;min-height:44px;cursor:pointer;color:#1a518f;font-size:13px;font-weight:800;line-height:1.5}
.ea6l-filters summary:focus-visible,.ea6l-info summary:focus-visible{outline:3px solid #82b5ff;outline-offset:2px}
.ea6l-filter-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding:0 0 15px}
.ea6l-actions{display:flex;justify-content:flex-end;align-items:center;margin-top:10px}
.ea6l-actions a{font-size:12px;color:#19549c;font-weight:750;text-decoration:underline;min-height:40px;display:inline-flex;align-items:center}
.ea6l-info{border:1px solid #e0e9f4;border-radius:10px;padding:0 12px;margin-bottom:14px;background:#f7faff}
.ea6l-info summary{padding:11px 0;min-height:42px;cursor:pointer;color:#365675;font-size:12px;font-weight:750}
.ea6l-info .ea-score-guidance{margin:0;padding-bottom:12px}
@media(max-width:680px){.ea6l-search-row{align-items:stretch;flex-direction:column}.ea6l-search-row .ea-tool-field,.ea6l-submit{width:100%;flex:initial}.ea6l-filter-grid{grid-template-columns:minmax(0,1fr)}}
'''
    if not s.count('</style>') == 2: raise ValueError(f'{n}: stylesheet structure changed')
    s=s.replace('</style>', css+'\n</style>',1)
    s=once(s, '''    <a
      href="#ea-filter-hobby"
      class="ea-change-city"
    >
      Filter by hobby &#8595;
    </a>
''','',n)
    s=once(s, '      <span class="ea-discovery-count">{{ total_attractions }} of {{ published_total }} published</span>\n', '',n)
    start='    <form class="ea-tools-form" method="get" action="{% url \'places:attraction_carousel\' %}" role="search">'
    left=s.index(start)
    right=s.index('    </form>',left)+len('    </form>')
    original=s[left:right]
    # Preserve same input/select markup from source so logic and Django context stay stable.
    search=re.search(r'(      <div class="ea-tool-field">\s*<label for="ea-search-query">.*?</div>)',original,re.S)
    categories=re.search(r'(      <div class="ea-tool-field">\s*<label for="ea-filter-category">.*?</div>)',original,re.S)
    hobbies=re.search(r'(      <div class="ea-tool-field">\s*<label for="ea-filter-hobby">.*?</div>)',original,re.S)
    sort=re.search(r'(      <div class="ea-tool-field">\s*<label for="ea-filter-sort">.*?</div>)',original,re.S)
    if not all((search,categories,hobbies,sort)): raise ValueError(f'{n}: discovery form structure changed')
    form='''    <form class="ea6l-tools-form" method="get" action="{% url 'places:attraction_carousel' %}" role="search">
      <div class="ea6l-search-row">
'''+search.group(1)+'''
        <button type="submit" class="ea6l-submit">Search places →</button>
      </div>
      <details class="ea6l-filters" {% if selected_category or selected_hobby or selected_sort != 'recommended' %}open{% endif %}>
        <summary>More filters · Category, hobby and sorting</summary>
        <div class="ea6l-filter-grid">
'''+categories.group(1)+'\n'+hobbies.group(1)+'\n'+sort.group(1)+'''
        </div>
      </details>
      {% if search_query or selected_category or selected_hobby or selected_sort != 'recommended' %}
        <div class="ea6l-actions"><a href="{% url 'places:attraction_carousel' %}?browse=all">Clear search and filters</a></div>
      {% endif %}
    </form>'''
    s=s[:left]+form+s[right:]
    old='<p class="ea-score-guidance" id="ea-score-guidance">Finding a destination with search or filters does not mean it matches your personal hobbies. Personalized relevance is calculated using selected hobbies and available ratings, normalized over available signals. A lower percentage is not a destination-quality rating. No GPS distance is scored. Gray map markers mean there is not enough personalization information; colored map markers use the displayed score.</p>'
    new='<details class="ea6l-info"><summary>How recommendation scores and map markers work</summary>'+old+'</details>'
    s=once(s,old,new,n)
    if s.count('ea6l-tools-form')!=1: raise ValueError('form duplication')
    return s


def patch_nearby(s):
    n='templates/places/nearby_places.html'
    css='''
/* exploreanywhere-phase6l-visitor-ux-v1: less explanatory clutter */
.ea6l-privacy-short{font-size:12px;line-height:1.5;color:#526c84;margin:10px 0 0}
.ea6l-privacy{margin-top:10px;border:1px solid #dde8f4;background:#f9fbff;border-radius:11px;padding:0 12px}
.ea6l-privacy summary{font-size:12px;font-weight:750;color:#26588c;padding:11px 0;min-height:42px;cursor:pointer}
.ea6l-privacy summary:focus-visible{outline:3px solid #8ab8ff;outline-offset:2px}
.ea6l-privacy .ea6-warning{margin:0 0 12px}
@media(max-width:760px){.ea6-search input,.ea6-search select{font-size:16px}.ea6-quick a{min-height:44px}}
'''
    s=once(s,'</style>',css+'\n</style>',n)
    s=once(s,'Find verified destinations and businesses in Kabankalan City. Explore by hobbies, search for local services, or check nearby places.', 'Search published Kabankalan places and businesses, then view them on a map or compare their distances.',n)
    s=once(s,'<a href="{% url \'places:attraction_carousel\' %}?mode=nearby">Clear search</a>', '''{% if query or selected_service %}<a href="{% url 'places:attraction_carousel' %}?mode=nearby">Clear search</a>{% endif %}''',n)
    category_mappings=[('coffee','Coffee'),('restaurant','Restaurants'),('barber','Barbers'),('mall','Malls'),('billiards','Billiards')]
    for cat,label in category_mappings:
        old=f'<a href="{{% url \'places:attraction_carousel\' %}}?mode=nearby&amp;service={cat}">'
        new=f'<a href="{{% url \'places:attraction_carousel\' %}}?mode=nearby&amp;service={cat}" {{% if selected_service == \'{cat}\' %}}aria-current="true"{{% endif %}}>'
        s=once(s,old,new,n)
    note='<p class="ea6-warning">Your precise GPS coordinates are used only inside this browser page; they are not sent to ExploreAnywhere. GPS generally needs HTTPS on Android (localhost is an exception). Distances are straight-line estimates, not driving times. Places shown are Kabankalan listings; location permission does not independently verify city boundaries.</p>'
    s=once(s,note,'''<p class="ea6l-privacy-short">GPS stays in this browser. Distances are approximate straight-line estimates.</p>
    <details class="ea6l-privacy"><summary>GPS, privacy and distance details</summary>'''+note+'''</details>''',n)
    return s


def patch_home(s):
    n='templates/home.html'
    css='''
/* exploreanywhere-phase6l-visitor-ux-v1: useful hobby shortcuts */
#hobbies a.ea6l-hobby-link{display:flex;color:inherit;text-decoration:none;cursor:pointer}
#hobbies a.ea6l-hobby-link:focus-visible{outline:3px solid #1769ff;outline-offset:4px}
#hobbies a.ea6l-hobby-link:hover h3{color:#0757d8}
'''
    s=once(s,'</style>',css+'\n</style>',n)
    s=once(s,'Choose your interests and discover places that fit\n                your lifestyle, wherever your journey takes you.','Select an interest to search published Kabankalan places. Results depend on verified listings.',n)
    for label,query in [('Billiards','billiards'),('Basketball','basketball'),('Café Hopping','coffee'),('Hiking','hiking'),('Gaming','gaming'),('Photography','photography'),('Food Trips','restaurants'),('Nature & Outdoors','nature')]:
        pattern=re.compile(r'<div class="hobby-card">(?P<interior>\s*<div class="hobby-emoji">.*?</div>\s*<h3>'+re.escape(label)+r'</h3>\s*<p>.*?</p>\s*)</div>',re.S)
        result,c=pattern.subn(lambda m: '''<a class="hobby-card ea6l-hobby-link" href="{% url 'places:smart_search' %}?q='''+query+'''" aria-label="Search Kabankalan places for '''+label+'''">'''+m.group('interior')+'</a>',s,count=1)
        if c!=1: raise ValueError(f'{n}: expected one hobby card {label}, found {c}')
        s=result
    return s

PATCHERS={
 'templates/places/_discovery_modes.html':patch_modes,
 'templates/places/attraction_carousel.html':patch_carousel,
 'templates/places/nearby_places.html':patch_nearby,
 'templates/home.html':patch_home,
}


def patch_content(name,raw):
    if MARKER in raw: raise ValueError(f'{name}: Phase 6L is already installed')
    return PATCHERS[name](raw)
