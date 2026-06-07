"""Generate synthetic free-text synopses for titles and write to title_descriptions.csv."""

from __future__ import annotations

import hashlib
import os
import random
from pathlib import Path

import pandas as pd

DATA_DIR = Path(os.getenv("KG_DATA_DIR", Path(__file__).with_name("kg_demo_data")))

# Templates by genre - use {type} placeholder for the content type label
_GENRE_TEMPLATES: dict[str, list[str]] = {
    "Action": [
        "A pulse-pounding {type} where a covert operative races against time to prevent a global catastrophe.",
        "An explosive {type} following a disgraced soldier who must go rogue to expose corruption at the highest levels of government.",
        "A high-octane {type} about a former special forces veteran pulled back into the field for one last impossible mission.",
        "An adrenaline-fueled {type} in which rival factions clash across three continents, leaving a trail of deception and betrayal.",
    ],
    "Drama": [
        "A powerful {type} exploring the fractured bonds between family members as they navigate grief, guilt, and reconciliation.",
        "An emotionally charged {type} about an individual's struggle to rebuild identity and purpose after an unexpected personal collapse.",
        "A nuanced {type} that examines the quiet cost of ambition and the unspoken sacrifices we make for the people we love.",
        "A tender yet unflinching {type} in which three strangers bound by a shared tragedy find unexpected solidarity.",
    ],
    "Comedy": [
        "A hilarious {type} following a group of well-meaning misfits whose cross-country trip descends into spectacular chaos.",
        "A witty {type} about a small-town dreamer who accidentally becomes the most controversial person in a major city.",
        "A charming {type} centered on a chaotic workplace where every attempt to impose order results in glorious failure.",
        "A sharp satirical {type} skewering corporate culture through the eyes of the most reluctant middle manager alive.",
    ],
    "Thriller": [
        "A gripping psychological {type} where a seasoned detective discovers the prime suspect may be hiding in plain sight.",
        "A suspenseful {type} about a cybersecurity analyst who uncovers a conspiracy that reaches the highest corridors of power.",
        "A taut {type} in which a forensic archivist realizes the cold cases stacking up on her desk share one terrifying pattern.",
        "A slow-burn {type} where a seemingly routine investigation peels back layers of a community's darkest secrets.",
    ],
    "Sci-Fi": [
        "A visionary science fiction {type} set in a near future where artificial intelligence has fundamentally reshaped what it means to be human.",
        "A thought-provoking {type} exploring the ethical fractures that open when deep-space colonization forces humanity to redefine citizenship.",
        "A cerebral science fiction {type} about a theoretical physicist whose containment breach tears a hole in the fabric of spacetime.",
        "A bleak yet hopeful {type} depicting a generation born on a generation ship who have never seen Earth and no longer believe in it.",
    ],
    "Horror": [
        "A terrifying {type} following a group of strangers stranded in a remote wilderness as something ancient and patient closes in.",
        "A chilling psychological {type} in which a family discovers their renovated home was built atop the site of something unspeakable.",
        "A bone-chilling {type} where a marine biologist's deep-sea expedition surfaces a creature that should not exist.",
        "A slow-dread {type} exploring the horror of losing trust in your own perception of reality.",
    ],
    "Documentary": [
        "A revealing documentary tracing the rise and fall of one of the most influential — and ruthless — figures in modern industry.",
        "An eye-opening documentary investigating the hidden environmental toll of the global fast-fashion supply chain.",
        "A deeply personal documentary following three displaced families across different continents as they confront climate migration.",
        "A meticulously reported documentary exposing the decade-long cover-up of a public health crisis that affected millions.",
    ],
    "Romance": [
        "A heartfelt {type} about two strangers whose lives intersect at a critical crossroads, leading to unexpected and inconvenient love.",
        "A bittersweet romantic {type} following star-crossed lovers whose timing always seems to be precisely, maddeningly off.",
        "A sweeping romance spanning three decades, exploring how first love quietly shapes every significant decision that follows.",
        "A tender {type} in which two people who built walls against vulnerability slowly and reluctantly dismantle them together.",
    ],
    "Animation": [
        "An imaginative animated {type} that takes a young protagonist on a breathtaking journey through a world governed by forgotten magic.",
        "A visually stunning animated {type} about an unlikely band of heroes who must defend their enchanted homeland from an ancient darkness.",
        "A heartwarming animated {type} that uses the adventures of misfit characters to explore belonging, courage, and found family.",
        "A bold animated {type} that challenges the boundaries of the form while delivering a story full of wit and genuine emotion.",
    ],
    "Historical": [
        "An epic historical {type} set at one of history's most volatile inflection points, witnessed through the eyes of ordinary people.",
        "A meticulously researched {type} that restores the forgotten heroes of a pivotal but poorly documented historical era.",
        "A sweeping {type} that dramatizes the political intrigues and quiet personal sacrifices behind a world-altering moment.",
        "A nuanced historical {type} that refuses to mythologize, revealing the deeply human contradictions of its iconic subjects.",
    ],
    "Mystery": [
        "A twisting mystery {type} where a small-town detective's cold case investigation unravels a conspiracy no one was meant to find.",
        "A labyrinthine mystery following an antiquarian archivist who discovers a centuries-old cipher pointing to a lethal contemporary secret.",
        "A puzzle-box {type} in which every answer unlocks a deeper and more dangerous question, right up to its final revelation.",
        "A cerebral mystery {type} where the detective's greatest obstacle is not the killer — but the blind spots in her own reasoning.",
    ],
    "Fantasy": [
        "An epic fantasy {type} set in a world where ancient prophecies are fracturing and the heroes chosen to fulfill them are deeply, dangerously flawed.",
        "A richly imagined {type} in which a young cartographer discovers that the maps she draws are slowly reshaping the world they depict.",
        "A dark fantasy {type} exploring what happens after the chosen hero refuses the call — and someone far less qualified answers instead.",
        "A lyrical {type} in which magic is dying, and the last practitioners must decide whether to hoard it or spend it saving others.",
    ],
    "Crime": [
        "A gritty crime {type} tracing the violent collision between an ambitious prosecutor and a crime syndicate that owns the city.",
        "A morally ambiguous {type} following a detective who discovers the evidence trail points directly back at her own precinct.",
        "A propulsive crime {type} set over 48 hours as a seasoned investigator races to locate a witness before the syndicate does.",
        "A character-driven {type} in which the line between the investigator and the criminal blurs with each episode.",
    ],
}

_GENRE_ALIASES: dict[str, str] = {
    "Action/Adventure": "Action",
    "Science Fiction": "Sci-Fi",
    "Sci-Fi": "Sci-Fi",
    "Romantic Comedy": "Romance",
    "Crime/Thriller": "Crime",
    "Crime Thriller": "Crime",
    "History": "Historical",
    "Animated": "Animation",
}

_TYPE_LABELS: dict[str, str] = {
    "Movie": "film",
    "TV Series": "series",
    "Documentary": "documentary",
    "Special": "special",
    "Miniseries": "limited series",
}


def _build_description(genre: str, title_type: str, studio: str, year: int, seed: int) -> str:
    rng = random.Random(seed)
    canonical = _GENRE_ALIASES.get(genre, genre)
    templates = _GENRE_TEMPLATES.get(canonical, _GENRE_TEMPLATES["Drama"])
    template = rng.choice(templates)
    type_label = _TYPE_LABELS.get(title_type, "production")
    narrative = template.format(type=type_label)
    return f"{narrative} Produced by {studio} ({year})."


def generate_descriptions() -> None:
    titles_path = DATA_DIR / "titles.csv"
    if not titles_path.exists():
        raise FileNotFoundError(f"titles.csv not found at {titles_path}")

    titles_df = pd.read_csv(titles_path)
    rows: list[dict[str, str]] = []

    for _, row in titles_df.iterrows():
        seed = int(hashlib.sha256(str(row["title_id"]).encode()).hexdigest(), 16) % (2**31)
        desc = _build_description(
            genre=str(row.get("genre", "Drama")),
            title_type=str(row.get("title_type", "Movie")),
            studio=str(row.get("studio", "Unknown Studio")),
            year=int(row.get("release_year", 2020)),
            seed=seed,
        )
        rows.append({"title_id": str(row["title_id"]), "synopsis": desc})

    out_path = DATA_DIR / "title_descriptions.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"Generated {len(rows)} descriptions → {out_path}")


if __name__ == "__main__":
    generate_descriptions()
