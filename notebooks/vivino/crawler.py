import sys
import requests
import bs4 as soup
import re
import argparse
import time

N_VOTES_REGEX = re.compile("(\d+) ratings")
RATING_REGEX = re.compile("Avg. Rating: (\d\.\d)")

URL_PREFIX = "https://www.vivino.com"

SEARCH_URL_PATTERN = "/search?q={query}&start={page}"

def crawl(url, parse_fun):    
    print "Crawling %s" % url
    r = requests.get(url)
    time.sleep(0.1)

    if r.status_code != requests.codes.ok:
        raise IOError("Failed to fetch page, status: %s", r.status_code)

    return parse_fun(r.text)


def parse_search_page(text):
    s = soup.BeautifulSoup(text, 'html.parser')

    results_div = s.find("div", class_="search-results-list")

    urls = []
    for wine_card in results_div.find_all("div", class_="wine-card-large"):        
        urls.append(URL_PREFIX + wine_card.find("div", class_="wine-information").h2.a['href'])

    next_button = s.find("button", attrs={"name": "start"}, string="Next")
    more_results = "disabled" not in next_button.attrs

    return urls, more_results


def parse_wine_page(text):
    s = soup.BeautifulSoup(text, 'html.parser')

    section = s.find("section", class_="wine-page")
    # Get winery and wine
    titles = section.find_all("span", class_="wine-info__title")
    if len(titles) != 1:
        raise ValueError("Found %d titles instead of 1" % len(titles))

    winery = titles[0].find("span", class_="wine-info__winery").a.string.strip()
    wine = titles[0].find("span", class_="wine-info__wine").string.strip()

    # Get raing and number of votes
    info = section.find_all("span", class_="wine-info__average-info")
    if len(info) != 1:
        raise ValueError("Found %d info instead of 1" % len(info))

    rating_search = RATING_REGEX.search(info[0].find("span", class_="average-info__rating").strings.next())
    if rating_search:
        rating = rating_search.group(1)
    votes_search = N_VOTES_REGEX.search(info[0].find("span", class_="text-small", string=N_VOTES_REGEX).string)
    if votes_search:
        votes = votes_search.group(1)

    # Get image url
    figures = section.find_all("figure", class_="header__image")
    if len(figures) != 1:
        raise ValueError("Found %d images instead of 1" % len(figures))
    image_url = "http://" + figures[0]['style'][24:-1]

    return {     
        "winery": winery, 
        "wine": wine, 
        "image_url": image_url, 
        "rating": rating, 
        "votes": votes
    }


def search(args):
    results_found = 0
    with open(args.u, "a") as uf:
        with open(args.q, "r") as qf:
            for i, line in enumerate(qf):
                query = line.strip()       
                if i + 1 >= args.n:                    
                    print "Crawling query %s" % query
                    search_page = 0
                    more_results = True
                    while more_results:
                        search_page += 1
                        url = URL_PREFIX + SEARCH_URL_PATTERN.format(query=query, page=search_page)
                        urls, more_results = crawl(url, parse_search_page)                   
                        for u in urls:
                            print >> uf, u
                            results_found += 1
                else:
                    print "Skipping query %s" % query
    print "Total pages found: %d" % results_found


def load(args):
    print args


def page(args):    
    print crawl(args.url, parse_wine_page)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_search = subparsers.add_parser('search', help='Search for wine page URLs')
    parser_search.add_argument('-q', type=str, help='a path to the text file with queries', default='queries.txt')
    parser_search.add_argument('-n', type=int, help='start from n-th line (1-based)', default=1)
    parser_search.add_argument('-u', type=str, help='output file path', default='urls.txt')
    parser_search.set_defaults(func=search)

    parser_load = subparsers.add_parser('load', help='Load images using a list of urls')
    parser_load.add_argument('-u', type=str, help='A path to the file with a list of wine URLs', default='urls.txt')
    parser_load.add_argument('-n', type=int, help='start from n-th line (1-based)', default=1)
    parser_load.set_defaults(func=load)

    parser_page = subparsers.add_parser('page', help='Parse single wine info url')
    parser_page.add_argument('url', type=str, help='url of a wine info page')
    parser_page.set_defaults(func=page)

    args = parser.parse_args(sys.argv[1:])
    args.func(args)

if __name__ == "__main__":
    main()