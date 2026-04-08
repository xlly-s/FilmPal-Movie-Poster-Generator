## imports

from PIL import Image, ImageFont, ImageDraw, ImageFilter
import requests
from io import BytesIO
import textwrap
import asyncio


## varible (CHANGE API)
TMDB_API_KEY = "api_key"
TMDB_BASE    = "https://api.themoviedb.org/3"
IMG_POSTER   = "https://image.tmdb.org/t/p/w500"
IMG_BACKDROP = "https://image.tmdb.org/t/p/w1280"



## sub routines

def searchfilm(query: str) -> list:
    r = requests.get(f"{TMDB_BASE}/search/movie",
                     params={"api_key": TMDB_API_KEY, "query": query})
    r.raise_for_status()
    return r.json().get("results", [])


def getfilmdetail(movie_id: int) -> dict:
    r = requests.get(f"{TMDB_BASE}/movie/{movie_id}",
                     params={"api_key": TMDB_API_KEY})
    r.raise_for_status()
    return r.json()


def selectfilm(query: str) -> dict:
    results = searchfilm(query)
    if not results:
        raise ValueError(f"No movies found : {query!r}")
    if len(results) == 1:
        return getfilmdetail(results[0]["id"])
    print("\nLots of matches found:")
    for i, m in enumerate(results[:8]):
        year = (m.get("release_date") or "")[:4]
        print(f"  [{i+1}] {m['title']} ({year})")
    choice = input("\nMake a selection (or Enter for #1): ").strip()
    idx = (int(choice) - 1) if choice.isdigit() else 0
    idx = max(0, min(idx, len(results) - 1))
    return getfilmdetail(results[idx]["id"])


## data - ported from FilmBuddy-Reborn (Thanks Anand Murthy)

class imagedata:
    def __init__(self, title, year, description, rating, link, genre, language):
        self.title       = title
        self.year        = year
        self.description = description
        self.rating      = round(rating, 1) if rating is not None else None
        self.link        = link
        self.genre       = genre
        self.language    = language

    @staticmethod
    def rgb(p):
        d = [255, 0, 0]
        d[1] = int((510 * p) / 100)
        if d[1] > 255:
            d[0] -= d[1] - 255
            d[1] = 255
        return tuple(d)

    def makeimage(self):
        try:
            poster = Image.open(BytesIO(requests.get(self.link).content))
        except Exception:
            poster = Image.new("RGB", (300, 450), (30, 30, 30))

        image = Image.new("RGB", (2400, 1000), color=(38, 38, 38))
        poster = poster.resize((898, 1012))
        image.paste(poster, (image.size[0] - poster.size[0], 0))

        try:
            blurman = Image.open("Blurman.png")
            image.paste(blurman, (0, 0), mask=blurman)
        except FileNotFoundError:
            pass 

        draw       = ImageDraw.Draw(image)
        title_font = self._font("fonts/ubuntu.ttf", 105)
        desc_font  = self._font("fonts/arial.ttf",  55)
        year_font  = self._font("fonts/arial.ttf",  60)
        actor_font = self._font("fonts/coco.ttf",   55)
        rate_font  = self._font("fonts/ubuntu.ttf", 90)

        if self.title:
            draw.text((1, 1), self.title, (255, 238, 0), font=title_font)
        if self.year:
            draw.text((5, title_font.getbbox(self.title)[3] + 5),
                      str(self.year), (255, 238, 0), font=year_font)

        txt_x, txt_y = 3, 230
        if self.description:
            for line in textwrap.wrap(self.description, width=65)[:4]:
                draw.text((txt_x, txt_y), line, (255, 255, 255), font=desc_font)
                txt_y += 60
        txt_y += 45

        if self.rating is not None:
            draw.text((txt_x, txt_y), "Rating:", (255, 238, 0), font=actor_font)
            rw = actor_font.getbbox("Rating:")[2]
            draw.text((rw + 20, txt_y - 17), str(self.rating),
                      self.rgb(float(self.rating) * 10), font=rate_font)
            txt_y += 135

        if self.genre:
            draw.text((txt_x, txt_y), "Genre:", (255, 238, 0), font=actor_font)
            gw = actor_font.getbbox("Genre:")[2]
            draw.text((gw + 20, txt_y + 7), ", ".join(self.genre),
                      (255, 255, 255), font=desc_font)
            txt_y += 135

        if self.language:
            draw.text((txt_x, txt_y), "Language:", (255, 238, 0), font=actor_font)
            lw = actor_font.getbbox("Language:")[2]
            draw.text((lw + 20, txt_y + 7), self.language,
                      (255, 255, 255), font=desc_font)

        image.show()
        return image

    @staticmethod
    def _font(path, size):
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            return ImageFont.load_default()


## creatorr

class designer(imagedata):
    def __init__(self, title, year, description, rating, link, genre, language,
                 backdrop, resval=2):
        super().__init__(title, year, description, rating, link, genre, language)
        self.backdrop   = backdrop
        self.w          = 420 * resval
        self.h          = 220 * resval
        self.fontsizes  = (self.w + self.h) // 64
        self.genresizes = (self.w + self.h) // 100

    async def design(self) -> Image.Image:
        try:
            poster = Image.open(BytesIO(requests.get(self.link).content))
        except Exception:
            poster = Image.new("RGB", (300, 450), (30, 30, 30))

        background = Image.new("RGB", (self.w, self.h), color=(0,) * 3)
        background = await self.makebackground(background, poster)
        await asyncio.gather(
            self.deploytext(background, (self.w + self.h) // 96, (self.w + self.h) // 96),
            self.genregenerator(background, x=(self.w + self.h) // 96, y=self.h - self.h // 12),
        )
        return background

    async def makebackground(self, background, poster):
        fposter = poster.resize((background.size[0] // 3, background.size[1]))
        await self.pasteposter(background, fposter)
        if self.link is not None:
            await self.bg(background, poster, fposter)
        return background

    async def deploytext(self, bg, text_w, text_h):
        draw     = ImageDraw.Draw(bg)
        font     = self._font("fonts/lemon.otf", self.fontsizes)
        fontlang = self._font("fonts/lemon.otf", font.size * 2)
        fontdesc = self._font("fonts/robotoo.ttf", font.size)
        ratfont  = self._font("fonts/lemon.otf", font.size * 2)

        if self.year:
            draw.text((text_w, text_h), self.year, (182, 182, 182), font=font)
        if self.title:
            text_h += font.getbbox("a")[3]
            for line in textwrap.wrap(self.title, width=22)[:2]:
                draw.text((text_w, text_h), line.upper(), (255, 255, 255), font=fontlang)
                text_h += fontlang.getbbox("a")[3]
        if self.language:
            draw.text((text_w, text_h), self.language.upper(), (182, 182, 182), font=font)
        if self.description:
            text_h += font.getbbox("a")[3] * 3
            wrapper = textwrap.wrap(self.description, width=60)[:4]
            wrapper[-1] += " »"
            for line in wrapper:
                draw.text((text_w, text_h), line, (255, 255, 255), font=fontdesc)
                text_h += fontdesc.size
        if self.rating is not None:
            text_h += font.size * 2
            draw.text((text_w, text_h), str(self.rating),
                      self.rgb(float(self.rating) * 10), font=ratfont)

    async def bg(self, background, poster, origpost):
        if self.backdrop:
            bg_poster = Image.open(BytesIO(requests.get(self.backdrop).content))
        else:
            bg_poster = await self.cropcenter(poster)
        bg_poster = bg_poster.filter(ImageFilter.GaussianBlur(radius=25))
        bg_poster = bg_poster.resize((background.size[0], background.size[1]))
        bg_poster = await self.reduceopac(bg_poster)
        masker    = await self.imagemask(origpost)
        background.paste(bg_poster, (0, 0), masker)

    async def pasteposter(self, background, poster):
        background.paste(poster, (background.size[0] - background.size[0] // 3, 0))

    async def imagemask(self, post):
        mask = Image.new("L", (self.w, self.h), 0)
        draw = ImageDraw.Draw(mask)
        draw.polygon((
            (0, 0),
            (self.w - self.w // 3 + post.size[0] // 6, 0),
            (self.w - self.w // 3, self.h),
            (0, self.h),
        ), fill=255)
        return mask

    async def cropcenter(self, img):
        return img.crop((0, img.size[1] // 3, img.size[0], img.size[1] - img.size[1] // 3))

    async def reduceopac(self, img):
        img   = img.convert("RGB")
        black = Image.new("RGB", img.size, color=(0, 0, 0))
        return Image.blend(img, black, alpha=0.7)

    async def genregenerator(self, im, x, y, radius=None):
        gefont = self._font("fonts/robotoo.ttf", self.genresizes)
        width  = gefont.getbbox("A")[3] * 2
        draw   = ImageDraw.Draw(im)
        radius = width // 2
        for genre in self.genre:
            font_w = gefont.getbbox(genre)[2]
            rect_w = font_w + radius * 2
            draw.rounded_rectangle((x, y, x + rect_w, y + width), radius, (204,) * 3)
            draw.text((x + radius, y + width // 4.5), genre, (0,) * 3, font=gefont)
            x += rect_w + radius
        return im



def makeposter(query: str, style: str = "designer", resval: int = 2):
    """
    style = "designer"  -> Designer class (blurred backdrop, pill genres)
    style = "classic"   -> original imagedata style (yellow text, Blurman overlay)
    """
    film = selectfilm(query)

    title       = film.get("title") or film.get("original_title", "")
    year        = (film.get("release_date") or "")[:4]
    description = film.get("overview", "")
    rating      = film.get("vote_average") or 0.0
    language    = film.get("original_language", "").upper()
    genre       = [g["name"] for g in film.get("genres", [])]
    poster_path  = film.get("poster_path")
    backdrop_path = film.get("backdrop_path")
    link        = IMG_POSTER   + poster_path   if poster_path   else None
    backdrop    = IMG_BACKDROP + backdrop_path if backdrop_path else None

    if style == "classic":
        obj = imagedata(title, year, description, rating, link, genre, language)
        return obj.makeimage()
    else:
        obj = designer(title, year, description, rating, link, genre, language,
                       backdrop, resval=resval)
        img = asyncio.run(obj.design())
        img.show()
        return img
# smash it all together

if __name__ == "__main__":
    query = input("Enter a film name: ").strip()
    style = input("style — 'designer' (normal) or 'classic' (boring): ").strip() or "designer"
    image = makeposter(query, style=style)
    save  = input("save to file? (Enter to skip): ").strip()
    if save:
        image.save(save if "." in save else save + ".png")
        print(f"saved to {save}")
