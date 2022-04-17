import os
from multiprocessing import Pool

import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
from tqdm import tqdm


def get_letters_links():
    page = requests.get("https://pesnihi.com")
    soup = bs(page.text, "html.parser")
    all_pages = soup.findAll("div", {"class": "letters-block"})
    all_pages = all_pages[0].findAll("a")
    links = ["https://pesnihi.com" + page["href"] for page in all_pages]
    return links


def get_artists_links(links):
    artists_links = []
    for letter_link in tqdm(links, desc="Getting artists urls. Letters"):
        page = requests.get(letter_link)
        soup = bs(page.text, "html.parser")
        table = soup.find("table", {"class": "table is-striped"})
        all_pages = table.findAll("a")
        artists_links.extend([page["href"] for page in all_pages])
    return artists_links


def get_songs_links(links):
    songs_links = []
    for letter_link in tqdm(links, desc="Getting songs urls. Artists"):
        page = requests.get(letter_link)
        soup = bs(page.text, "html.parser")
        table = soup.find("table", {"class": "table is-striped"})
        if table is not None:
            all_pages = table.findAll("a")
            songs_links.extend([page["href"] for page in all_pages])
    return songs_links


def get_songs_pages(links):
    links2download = []
    for link in links:
        if not os.path.exists("./cache/" + link[8:].replace("/", "_")):
            links2download.append(link)
    for link in tqdm(links2download, desc="Downloading pages"):
        with open("./cache/" + link[8:].replace("/", "_"), 'wb') as out:
            out.write(requests.get(link).content)


def get_song_data(link):
    entry = {"link": link}

    if not os.path.exists("./cache/" + link[8:].replace("/", "_")):
        return

    with open("./cache/" + link[8:].replace("/", "_"), 'rb') as inp:
        soup = bs(inp.read(), 'html.parser')

    if soup.find("h1", {"class": "entry_title"}) is None:
        return None
    entry_title = soup.find("h1", {"class": "entry_title"}).text.split(" - ")
    entry["artist"] = entry_title[0][12:].replace(";", "")
    entry["title"] = entry_title[1].replace(";", "")
    entry_text = soup.find("div", {"class": "column song_content_column"})
    if entry_text is None:
        return None
    entry["text"] = " ".join(entry_text.text.replace("\n", " ").split()).replace(";", "")
    return entry


if __name__ == "__main__":
    if os.path.exists("./songs_links"):
        with open("songs_links", "r") as inp:
            songs_links = inp.readlines()
    else:
        artists_links = get_letters_links()
        artists_pages = get_artists_links(artists_links)
        songs_links = get_songs_links(artists_pages)
        with open("songs_links", "w") as out:
            out.writelines([link + "\n" for link in songs_links])

    if os.path.exists("./dataset.csv"):
        dataset = pd.read_csv("./dataset.csv", sep=";")
    else:
        songs_links = [link[:-1] for link in songs_links]

        get_songs_pages(songs_links)
        with Pool(6) as p:
            data = list(tqdm(p.imap(get_song_data, songs_links), total=len(songs_links)))
        data = list(filter(lambda x: x is not None, data))
        dataset = pd.DataFrame.from_records(data)
        dataset.to_csv("dataset.csv", index=False, sep=";")
