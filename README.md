# Sandbox Empire — tartományréteg (prototípus)

A `hex_engine_turns.py` motorra épül: ugyanaz az axiális hexmatematika, A* útkeresés,
Dijkstra flood-fill, kör- és mozgáspont-rendszer — most egy tartománytérképet hajt.

## Futtatás

```
pip install pygame        # vagy: pip install pygame-ce
python main.py            # véletlen térkép
python main.py 7          # adott seed
python simulate.py 40 7   # fejnélküli szimuláció 40 évszakra (balanszoláshoz)
```

## Fájlok

| Fájl | Tartalom |
|---|---|
| `hexcore.py` | Hexmatek, A*, flood-fill — súlyozott lépésköltséggel. Ugyanaz a flood-fill szolgálja a mozgást és a területfoglalást (több forrásból). |
| `world.py` | A szabályok, pygame nélkül: térképgenerálás, tartományok, hexállapotok, építmények, évszakok, pontok, hűség, NPC-urak. |
| `main.py` | Pygame-felület: térkép, határok, ikonok, oldalpanel, a király mozgatása. |
| `simulate.py` | Szabályok futtatása UI nélkül, összefoglalóval. |
| `data/province_meters.json` | A tartománymérők (Integráció, Letelepedés) küszöbei és értékei. |

## Irányítás

| Billentyű | |
|---|---|
| Bal klikk | tartomány / király kijelölése; célmező választása |
| Jobb klikk | mégse / kijelölés törlése |
| `I` / `E` / `L` | Irtás / Építés / Lakoma a kijelölt tartományban |
| `1`–`9` | építési lehetőség választása |
| `K` | a királyra ugrik és kijelöli · `N` következő saját tartomány |
| `H` | a király helyben marad ebben az évszakban |
| Nyilak / WASD / középső gomb húzása | térkép görgetése |
| `SPACE` / `ENTER` | évszak vége |

## Szabályok röviden

- **Idő:** 1 kör = 1 évszak, Kr. u. 481 tavaszától. Ősszel van az aratás (×3), télen nincs termés, és a munka is fele olyan gyors.
- **Hexállapot:** vadon → szántó → falu → városnegyed. Irtással lesz szántó (terepfüggő ár és idő). Ősszel egy szántó faluvá nőhet, ha van körülötte elég szántó. Városnegyed építéssel jön létre, vár, egyház vagy a székhely mellett.
- **Egy munka tartományonként:** irtás vagy egy építési fokozat. A munkaerő a tartomány méretével nő.
- **Építményvonalak:** Vár (Földvár → Palánkvár → Lakótorony → Kővár, ez adja a lovagokat), Egyház (Fakápolna → … → Katedrális, ez téríti a tartományt és tekintélyt ad), Kolostor (gyorsabb irtás, több termés; nem pogány tartományban), Piac (ezüst; római úton több), Palota (csak királyi birtokon, lassítja a hűség kopását).
- **Helyi pont:** szolgáltatás. Tartományonként raktározódik, évszakonként 15%-a megromlik.
- **Globális pontok:** ezüst; presztízs (évente kopik, nagy építmények és lakoma növelik); tekintély (plafonja 20, az egyházak növelik, a vazallusnak adott parancsra költöd).
- **Hűség:** 4 fokozat. Ha a király 8 évszakig nem látogat egy tartományt, egy fokkal romlik. Látogatáskor javul, lakomával akár Odaadóig is. Templom után nem eshet Lázongóig.
- **Király:** egység a térképen. Ahol tartózkodik, ott a vazallus ingyen kap parancsot, és lakoma rendezhető.
- **Tartománymérők:** Integráció (0–5) és Letelepedés (0–4) tartományonként. Csak a király tartományaiban fejlődnek (egyház, a király jelenléte, lovagok), és soha nem csökkennek. A Feszültség a kettő arányának különbsége; egyelőre csak kijelzés, események nem indulnak belőle. A királyi birtokok a maximumról indulnak, a többi tartomány nulláról, és amíg nincs behódolás, ott nem mozdulnak.
- **NPC-urak:** a független törzsek és a vazallus a jellemvonásuk szerint döntenek (Jámbor: egyház; Harcias: vár és irtás; Szorgos: irtás és piac; Rest: gyakran semmit).
