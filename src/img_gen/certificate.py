from PIL import Image, ImageFont, ImageDraw
import requests
from utils import icon_url
import io
from riot import UserInfo, Rank, RankOption

division_colors: dict[RankOption, str] = {
    'IRON': 'darkred',
    'SILVER': 'silver',
    'GOLD': 'darkgoldenrod',
    'PLATINUM': 'cadetblue',
    'EMERALD': 'limegreen',
    'DIAMOND': 'deepskyblue',
    'MASTER': 'magenta',
    'GRANDMASTER': 'firebrick',
    'CHALLENGER': 'dodgerblue'
}


class Certificate:
    user: UserInfo
    rank: Rank

    im: Image.Image
    draw: ImageDraw.ImageDraw
    w: int
    h: int

    def __init__(self, user: UserInfo, rank: Rank) -> None:
        self.user = user
        self.rank = rank

    def build_image(self) -> None:
        self.im = Image.open('assets/certificate-template.png')
        self.w, self.h = self.im.width, self.im.height
        self.draw = ImageDraw.Draw(self.im)

        self.draw_logo()

        self.center_text(
            'Congratulations!'.upper(),
            (self.w * 0.5, self.h * 0.24),
            ImageFont.truetype(
                "assets/fonts/Beaufort/BeaufortforLOL-Bold.ttf", 110)
        )

        self.center_text(
            'for',
            (self.w * 0.5, 570),
            ImageFont.truetype(
                "assets/fonts/Spiegel/Spiegel_TT_SemiBold_Italic.ttf", 30)
        )

        self.draw_user()

        self.center_text(
            f"Playing {self.rank.games()} Games!",
            (self.w * 0.5, 660),
            ImageFont.truetype(
                "assets/fonts/Spiegel/Spiegel_TT_SemiBold.ttf", 100)
        )

        self.draw_division()

        wr = self.rank.wins / self.rank.games()
        if wr >= 0.6:
            winrate_color = 'forestgreen'
        elif wr >= 0.4:
            winrate_color = 'darkgoldenrod'
        else:
            winrate_color = 'red'

        self.center_text(
            f'WR {self.rank.winrate()}',
            (472, 820),
            ImageFont.truetype(
                "assets/fonts/Beaufort/BeaufortforLOL-Bold.ttf", 60),
            winrate_color
        )

        self.center_text(
            self.rank.full(),
            (1091, 805),
            ImageFont.truetype(
                "assets/fonts/Beaufort/BeaufortforLOL-Bold.ttf", 45),
            division_colors.get(self.rank.division, 'black')
        )

        self.center_text(
            f'({self.rank.lp} LP)',
            (1091, 840),
            ImageFont.truetype(
                "assets/fonts/Beaufort/BeaufortforLOL-Bold.ttf", 30),
            division_colors.get(self.rank.division, 'black')
        )

        self.center_text(
            'At Completion Time',
            (1091, 885),
            ImageFont.truetype(
                "assets/fonts/Spiegel/Spiegel_TT_SemiBold_Italic.ttf", 30),
            'black'
        )

    def save(self, filename: str) -> None:
        self.im.save(filename, 'png')

    def center_text(self, text: str, pos: tuple[float, float], font: ImageFont.FreeTypeFont, color=(0, 0, 0)):
        text_pos = (int(pos[0]), int(pos[1]))
        self.draw.text(text_pos, text, color, anchor='mm', font=font)

    def get_img_from_url(self, url: str):
        res = requests.get(url)
        if not res.ok:
            print(res)
            raise Exception(res.text)

        return Image.open(io.BytesIO(res.content))

    def draw_user(self, padding=30, max_width=954):
        y_pos = 540

        fontsize, total_w = 125, max_width + 1
        while total_w > max_width:
            fontsize -= 5
            font = ImageFont.truetype(
                "assets/fonts/Beaufort/BeaufortforLOL-Regular.ttf", fontsize)
            total_w = fontsize + padding + \
                font.getlength(self.user.summoner_name)

        icon_im = self.get_img_from_url(
            icon_url(self.user.icon)).resize((fontsize, fontsize))

        icon_pos = (
            int((self.w - total_w) / 2),
            int(y_pos - icon_im.height)
        )

        text_pos = (
            int((self.w + total_w) / 2),
            int(y_pos - icon_im.height / 2)
        )

        self.im.paste(icon_im, icon_pos)
        self.draw.text(text_pos, self.user.summoner_name,
                       (0, 0, 0), anchor='rm', font=font)

    def draw_division(self, size=280):
        im = Image.open(f'assets/ranks/{self.rank.division.lower()}.png')
        im = im.resize((size, int(size / im.width * im.height)))
        img_pos = (int((self.w - im.width) / 2), int(700))
        self.im.paste(im, img_pos, im)

    def draw_logo(self, height=50):
        im = Image.open('assets/logo.png')
        im = im.resize((int(height / im.height * im.width), height))
        img_pos = (int((self.w - im.width) / 2), 50)
        self.im.paste(im, img_pos)


if __name__ == '__main__':
    cert = Certificate(UserInfo(summoner_name='KAPPAMAC',
                       icon=12), rank=Rank('CHALLENGER', None, 999, 499, 1))
    cert.build_image()
    cert.save('temp/output.png')
