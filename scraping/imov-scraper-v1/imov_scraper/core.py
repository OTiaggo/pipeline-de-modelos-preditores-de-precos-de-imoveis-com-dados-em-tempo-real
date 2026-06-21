import asyncio
import hashlib
import itertools
import json
import logging
import random
import re
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)


@dataclass
class Imovel:
    external_id: str
    url: str
    site: str
    titulo: str
    finalidade: str
    tipo: str
    preco: float
    bairro: str
    cidade: str
    estado: str
    area_m2: Optional[float] = None
    quartos: Optional[int] = None
    banheiros: Optional[int] = None
    vagas: Optional[int] = None
    suites: Optional[int] = None
    andar: Optional[int] = None
    numero_endereco: Optional[str] = None
    preco_m2: Optional[float] = None
    condominio: Optional[float] = None
    iptu: Optional[float] = None
    descricao: Optional[str] = None
    endereco: Optional[str] = None
    rua: Optional[str] = None
    numero: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_lancamento: bool = False
    portaria: Optional[bool] = None
    vista_mar: Optional[bool] = None
    condominio_fechado: Optional[bool] = None
    piscina: Optional[bool] = None
    deck: Optional[bool] = None
    varanda_gourmet: Optional[bool] = None
    varanda: Optional[bool] = None
    academia: Optional[bool] = None
    salao_festa: Optional[bool] = None
    salao_jogos: Optional[bool] = None
    quadra_campo: Optional[bool] = None
    anuncio_criado: Optional[str] = None
    corretora: Optional[str] = None
    nota_media: Optional[float] = None
    imagem_url: Optional[str] = None
    data_coleta: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(s):
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    for a, b in [("ã","a"),("â","a"),("á","a"),("à","a"),("é","e"),("ê","e"),
                 ("í","i"),("ó","o"),("ô","o"),("õ","o"),("ú","u"),("ü","u"),
                 ("ç","c"),(" ","-")]:
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9\-]", "", s)


def _money_to_float(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"R\$\s*([\d\.]+)(?:,\d{1,2})?", text)
    if not m:
        return None
    try:
        v = float(m.group(1).replace(".", ""))
        return v if v >= 1 else None
    except Exception:
        return None


def _preco(t):
    v = _money_to_float(t or "")
    return v if v and v >= 100 else None


def _calc_preco_m2(preco: float, area: Optional[float]) -> Optional[float]:
    if preco and area and area > 5:
        return round(preco / area, 2)
    return None


RUA_RE = re.compile(
    r"^(Rua|R\.\s?|Av\.?\s|Avenida|Al\.?\s|Alameda|Trav\.?\s|Travessa|"
    r"Est\.?\s|Estrada|Rod\.?\s|Rodovia|Pça\.?\s|Praça|Largo|"
    r"Via\s|Viela|Beco|Calçada|Escadaria|Ladeira|Passagem|"
    r"Setor\s|Quadra\s|Lote\s)",
    re.I
)


def _tipo(t):
    t = (t or "").lower()
    if any(x in t for x in ["apart", "apto", "flat", "studio", "cobertura"]): return "apartamento"
    if any(x in t for x in ["casa", "sobrado", "village", "térrea", "terrea"]): return "casa"
    if any(x in t for x in ["terreno", "lote", "gleba"]): return "terreno"
    if any(x in t for x in ["comercial", "sala", "loja", "galpão", "galpao"]): return "comercial"
    if any(x in t for x in ["kitnet", "kitinete"]): return "kitnet"
    return "outro"


GENERIC_TITLES = {
    "destaque", "super destaque", "btb", "riva", "moura", "direcional",
    "tamanho do imóvel", "tamanho do imovel", "mota machado", "diagonal",
    "victa construtora", "fan construcoes", "unica incorporadora"
}

NEGATIVE_OLX_WORDS = [
    "ar condicionado", "ar-condicionado", "consul", "split", "mesa", "cadeira",
    "armário", "armario", "criado mudo", "bicicleta", "bike", "sapatilha",
    "geladeira", "fogão", "sofa", "sofá", "cama", "guarda roupa", "guarda-roupa"
]

IMOVEL_HINTS = [
    "casa", "apart", "apto", "terreno", "lote", "sala comercial", "loja", "galpão",
    "galpao", "kitnet", "quarto", "banheiro", "vaga", "m²", "m2", "aluguel",
    "financiamento", "condomínio", "condominio"
]

# Palavras da URL que são atributos/amenidades e não bairro.
URL_DROP_WORDS = {
    "venda", "aluguel", "comprar", "imovel", "apartamento", "casa", "condominio", "de", "da", "do", "das", "dos",
    "terrea", "terreno", "lote", "sala", "loja", "comercial", "quartos", "quarto", "banheiros", "banheiro", "vagas", "vaga",
    "com", "sem", "piscina", "mobiliado", "mobiliada", "closet", "churrasqueira", "cozinha", "americana", "academia",
    "playground", "varanda", "suite", "suites", "garagem", "elevador", "interfone", "gourmet", "portaria",
    "campo", "quadra", "fitness", "decorado", "novo", "pronto", "area", "servico", "serviço", "lazer", "privativa",
}

BAIRRO_FIX = {
    "coco": "Cocó",
    "dionisio torres": "Dionísio Torres",
    "joquei clube": "Jóquei Clube",
    "fatima": "Fátima",
    "jose de alencar": "José de Alencar",
    "edson queiroz": "Edson Queiroz",
    "luciano cavalcante": "Engenheiro Luciano Cavalcante",
    "engenheiro luciano cavalcante": "Engenheiro Luciano Cavalcante",
    "antonio bezerra": "Antônio Bezerra",
    "parque dois irmaos": "Parque Dois Irmãos",
    "varjota": "Varjota",
    "cidade dos funcionarios": "Cidade dos Funcionários",
    "mondubim": "Mondubim",
    "a mondubim": "Mondubim",
    "sao gerardo": "São Gerardo",
    "joao xxiii": "João XXIII",
    "jardim cearense": "Jardim Cearense",
    "lagoa redonda": "Lagoa Redonda",
    "parque iracema": "Parque Iracema",
    "bom jardim": "Bom Jardim",
    "benfica": "Benfica",
    "meireles": "Meireles",
    "aldeota": "Aldeota",
    "papicu": "Papicu",
    "passare": "Passaré",
    "messejana": "Messejana",
    "parangaba": "Parangaba",
    "cajazeiras": "Cajazeiras",
    "centro": "Centro",
    "pedras": "Pedras",
    "siqueira": "Siqueira",
    "montese": "Montese",
    "paupina": "Paupina",
    "serrinha": "Serrinha",
    "cambeba": "Cambeba",
    "sapiranga": "Sapiranga",
    "sapiranga coite": "Sapiranga/Coité",
    "coite": "Sapiranga/Coité",
    "cidade 2000": "Cidade 2000",
    "praia de iracema": "Praia de Iracema",
    "mucuripe": "Mucuripe",
    "guararapes": "Guararapes",

}

# Lista prática de bairros de Fortaleza usados para validar e limpar a saída.
# A estratégia é: se qualquer texto sujo contém um bairro conhecido, ficamos com o
# match mais específico/mais à direita. Isso resolve casos como
# "Rubens Monte 47 104Maraponga" e "Doutor Theberge 2021 01Presidente Kennedy".
BAIRROS_FORTALEZA = {
    "Aldeota", "Meireles", "Dionísio Torres", "Cocó", "Papicu", "Varjota", "Mucuripe",
    "Praia de Iracema", "Centro", "Fátima", "Benfica", "Montese", "Parangaba",
    "Bom Jardim", "Siqueira", "Mondubim", "Maraponga", "Serrinha", "Damas",
    "Vila União", "Jóquei Clube", "Presidente Kennedy", "Antônio Bezerra", "São Gerardo",
    "Parque Araxá", "Parquelândia", "Amadeu Furtado", "Rodolfo Teófilo", "Jacarecanga",
    "Carlito Pamplona", "Barra do Ceará", "Cristo Redentor", "Pirambu", "Álvaro Weyne",
    "Quintino Cunha", "Vila Velha", "Jardim Guanabara", "Floresta", "Ellery",
    "Engenheiro Luciano Cavalcante", "Guararapes", "Edson Queiroz", "Sapiranga/Coité",
    "Cambeba", "Messejana", "Lagoa Redonda", "José de Alencar", "Paupina", "Pedras",
    "Jangurussu", "Barroso", "Passaré", "Parque Dois Irmãos", "Parque Iracema",
    "Cajazeiras", "Cidade dos Funcionários", "Jardim Cearense", "Manuel Dias Branco",
    "Salinas", "Dunas", "Cais do Porto", "Vicente Pinzón", "De Lourdes", "Sabiaguaba",
    "Ancuri", "Coaçu", "Curió", "Guajeru", "São Bento", "Boa Vista", "Aerolândia",
    "Alto da Balança", "Dias Macedo", "Itaoca", "Itaperi", "Dendê", "Vila Peri",
    "Panamericano", "Couto Fernandes", "Demócrito Rocha", "Bonsucesso", "Henrique Jorge",
    "Autran Nunes", "João XXIII", "Granja Lisboa", "Granja Portugal", "Canindezinho",
    "Conjunto Ceará", "Conjunto Esperança", "Parque Presidente Vargas", "Aracapé",
    "Parque Santa Rosa", "Parque São José", "Manoel Sátiro", "Novo Mondubim", "Planalto Ayrton Senna",
}

# Garante que todos os bairros conhecidos também existam na tabela normalizada.
for _b in BAIRROS_FORTALEZA:
    BAIRRO_FIX.setdefault(_slug(_b).replace('-', ' '), _b)
BAIRRO_FIX.update({
    "sapiranga coite": "Sapiranga/Coité",
    "sapiranga coité": "Sapiranga/Coité",
    "coite": "Sapiranga/Coité",
    "coité": "Sapiranga/Coité",
    "presidente kennedy": "Presidente Kennedy",
    "doutor theberge presidente kennedy": "Presidente Kennedy",
    "rubens monte maraponga": "Maraponga",
})


_COMMERCIAL_WORDS = {"comercial", "sala", "loja", "galpao", "galpão", "conjunto", "ponto", "predio", "prédio", "corporativo", "escritorio", "escritório"}
_RESIDENTIAL_WORDS = {"apartamento", "apto", "apart", "casa", "condominio", "condomínio", "suite", "suíte", "dormitorio", "dormitório", "quarto", "garagem", "varanda"}


def _bairro_candidates_from_text(text: str):
    if not text:
        return []
    norm = _slug(str(text)).replace('-', ' ')
    norm = re.sub(r"\d+", " ", norm)
    norm = re.sub(r"\s+", " ", norm).strip()
    compact = norm.replace(' ', '')
    cands = []
    for key, pretty in BAIRRO_FIX.items():
        key_norm = _slug(key).replace('-', ' ')
        key_compact = key_norm.replace(' ', '')
        # match por palavra/frase inteira
        for m in re.finditer(rf"(?<![a-z]){re.escape(key_norm)}(?![a-z])", norm):
            cands.append((m.start(), len(key_norm), pretty))
        # match grudado: 104Maraponga, 01PresidenteKennedy, TerreoMondubim
        if len(key_compact) >= 6:
            pos = compact.rfind(key_compact)
            if pos >= 0:
                cands.append((pos, len(key_compact), pretty))
    # mais à direita e mais específico vence
    cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
    seen=[]
    for _,__,name in cands:
        if name not in seen:
            seen.append(name)
    return seen


def _best_bairro(*texts: str) -> str:
    joined = " | ".join([str(t or '') for t in texts])
    cands = _bairro_candidates_from_text(joined)
    return cands[0] if cands else ""


def _force_consistent_tipo(iv):
    txt = " ".join([iv.titulo or "", iv.url or "", iv.descricao or ""]).lower()
    txt_slug = _slug(txt).replace('-', ' ')
    if any(w in txt_slug for w in ["terreno", "lote", "gleba"]):
        return "terreno"
    if any(w in txt_slug for w in _COMMERCIAL_WORDS):
        # Só mantém comercial se há palavra comercial forte e não parece claramente residencial.
        if not any(w in txt_slug for w in ["apartamento", "casa", "quarto", "dormitorio", "suite"]):
            return "comercial"
        if "sala comercial" in txt_slug or "loja" in txt_slug or "galpao" in txt_slug or "galpão" in txt_slug:
            return "comercial"
    if any(w in txt_slug for w in ["apartamento", "apto", "flat", "studio", "cobertura"]):
        return "apartamento"
    if any(w in txt_slug for w in ["casa", "sobrado", "duplex", "terrea", "térrea"]):
        return "casa"
    # Se tem quartos e é área compatível, não deixar como comercial/outro sem evidência.
    if iv.quartos and iv.quartos >= 1:
        if iv.tipo in {"outro", "comercial"}:
            return "apartamento"
    return iv.tipo or "outro"


def _listing_id(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"(?:id-|/)(\d{8,13})(?:[/?#.-]|$)", url)
    return m.group(1) if m else ""


def _is_valid_record(iv) -> bool:
    if not iv.url or not iv.preco or iv.preco < 1000:
        return False
    if not iv.bairro:
        return False
    if iv.tipo == "outro" and not (iv.quartos or iv.area_m2):
        return False
    if iv.quartos and iv.quartos > 12 and iv.tipo not in {"comercial", "outro"}:
        return False
    if iv.area_m2 and (iv.area_m2 < 10 or iv.area_m2 > 50000):
        return False
    if iv.tipo in {"apartamento", "casa"} and iv.preco_m2 and (iv.preco_m2 < 300 or iv.preco_m2 > 35000):
        return False
    return True


def _merge_items(preferred, other):
    """Une campos úteis de registros duplicados, mantendo o melhor como base."""
    if not preferred: return other
    if not other: return preferred
    for f in [
        "descricao", "endereco", "rua", "numero", "numero_endereco", "condominio", "iptu", "area_m2",
        "quartos", "banheiros", "vagas", "suites", "andar", "portaria", "vista_mar",
        "condominio_fechado", "piscina", "deck", "varanda_gourmet", "varanda",
        "academia", "salao_festa", "salao_jogos", "quadra_campo", "anuncio_criado",
        "corretora", "nota_media", "imagem_url",
    ]:
        if getattr(preferred, f, None) in (None, "") and getattr(other, f, None) not in (None, ""):
            setattr(preferred, f, getattr(other, f))
    if not preferred.bairro and other.bairro:
        preferred.bairro = other.bairro
    preferred.tipo = _force_consistent_tipo(preferred)
    preferred.preco_m2 = _calc_preco_m2(preferred.preco, preferred.area_m2)
    return preferred


def _title_from_slug(slug: str) -> str:
    slug = re.sub(r"^(imovel|venda|aluguel|comprar|apartamento|casa|terreno|sala|loja|comercial)[-_/]+", "", slug or "")
    slug = re.sub(r"-id-?\d+.*$", "", slug)
    slug = re.sub(r"-venda-rs.*$", "", slug, flags=re.I)
    slug = re.sub(r"-aluguel-rs.*$", "", slug, flags=re.I)
    slug = re.sub(r"-\d+m2.*$", "", slug, flags=re.I)
    slug = slug.replace("-", " ").strip()
    return " ".join(w.capitalize() for w in slug.split())



def _extract_known_bairro(text: str) -> str:
    """Procura o bairro conhecido mais provável dentro de um texto sujo."""
    return _best_bairro(text)

def _normalize_bairro_name(b: str) -> str:
    b = re.sub(r"\s+", " ", (b or "").strip())
    b = re.sub(r"^(Lote|Academia|Playground|Com Piscina|Com Churrasqueira|Com Garagem)\s+", "", b, flags=re.I).strip()
    known = _extract_known_bairro(b)
    if known:
        return known
    key = _slug(b).replace("-", " ")
    return BAIRRO_FIX.get(key, b.title() if b.islower() else b)


def _clean_bairro(bairro: str) -> str:
    b = (bairro or "").strip()
    b = re.sub(r"^Endereço não informado", "", b, flags=re.I).strip()
    if not b: return ""
    bad = b.lower().strip()
    if bad in GENERIC_TITLES: return ""
    if any(x in bad for x in ["imobiliária", "imobiliaria", "corretores", "transações", "transacoes", "participacoes", "participações", "ltda", "s/a", "re/max", "construtora", "incorporadora"]):
        return ""
    return _normalize_bairro_name(b)


def _parse_title_zap(title: str, cidade: str, estado: str, finalidade: str) -> Optional[dict]:
    if not title: return None
    tipo = _tipo(title.split(" ")[0] if title else "")
    area = None
    m = re.search(r"([\d]+(?:[,\.][\d]+)?)\s*m²", title)
    if m:
        try: area = float(m.group(1).replace(",", "."))
        except: pass
    quartos = None
    m = re.search(r"(\d+)\s*quarto", title, re.I)
    if m: quartos = int(m.group(1))
    banheiros = None
    m = re.search(r"(\d+)\s*banheiro", title, re.I)
    if m: banheiros = int(m.group(1))
    vagas = None
    m = re.search(r"(\d+)\s*vaga", title, re.I)
    if m: vagas = int(m.group(1))
    bairro = ""
    m = re.search(r"\bem\s+(.+)$", title, re.I)
    if m:
        partes = [p.strip() for p in m.group(1).split(",")]
        cidade_norm = cidade.strip().lower()
        for i, p in enumerate(partes):
            if p.lower() == cidade_norm and i > 0:
                candidato = partes[i - 1].strip()
                if not RUA_RE.match(candidato) and len(candidato.replace(" ", "")) > 2:
                    bairro = candidato
                elif i > 1:
                    candidato2 = partes[i - 2].strip()
                    if not RUA_RE.match(candidato2) and len(candidato2.replace(" ", "")) > 2:
                        bairro = candidato2
                break
    return dict(tipo=tipo, area=area, quartos=quartos, banheiros=banheiros, vagas=vagas, bairro=_clean_bairro(bairro))


def _url_info(url: str, cidade: str, estado: str) -> dict:
    out = {}
    if not url: return out
    u = url.lower()
    out["is_lancamento"] = any(x in u for x in ["/lancamentos/", "/imoveis-lancamentos/"])
    if "apartamento" in u: out["tipo"] = "apartamento"
    elif "casa-de-condominio" in u or "/casa" in u or "-casa-" in u: out["tipo"] = "casa"
    elif "terreno" in u or "lote" in u: out["tipo"] = "terreno"
    elif "sala" in u or "loja" in u or "comercial" in u: out["tipo"] = "comercial"
    if "/aluguel" in u or "-aluguel-" in u: out["finalidade"] = "aluguel"
    elif "/venda" in u or "-venda-" in u: out["finalidade"] = "venda"

    m = re.search(r"/(?:imovel|propriedades)/([^/?#]+)", u)
    slug = m.group(1) if m else ""
    if not slug:
        m = re.search(r"/(?:imoveis-lancamentos|lancamentos)/([^/?#]+)", u)
        slug = m.group(1) if m else ""
    if slug:
        t = _title_from_slug(slug)
        if t and len(t) > 5:
            out["titulo"] = t[:120]
        known_slug_bairro = _extract_known_bairro(slug.replace("-", " "))
        if known_slug_bairro:
            out["bairro"] = known_slug_bairro
        cs = _slug(cidade)
        parts = slug.split("-")
        try:
            idx = parts.index(cs)
        except ValueError:
            idx = -1
        if idx > 0:
            left = []
            skip_next = False
            for part in parts[:idx]:
                if part.isdigit():
                    skip_next = True
                    continue
                if skip_next and part in {"quartos", "quarto", "banheiros", "banheiro", "vagas", "vaga"}:
                    skip_next = False
                    continue
                skip_next = False
                if part in URL_DROP_WORDS: continue
                if re.match(r"^\d+m2$", part): continue
                left.append(part)
            # tenta detectar bairro conhecido no slug inteiro; evita cortar "Bom Jardim" em "Bom"
            chosen = _extract_known_bairro(" ".join(left))
            if not chosen:
                for n in range(min(4, len(left)), 0, -1):
                    cand = " ".join(left[-n:])
                    if cand in BAIRRO_FIX:
                        chosen = cand
                        break
            if not chosen and left:
                chosen = " ".join(left[-3:])
            if chosen:
                out["bairro"] = _clean_bairro(chosen.replace("-", " "))
    return out


def _looks_like_olx_imovel(titulo: str, full: str, tipo: str, area=None, quartos=None) -> bool:
    text = f"{titulo or ''} {full or ''}".lower()
    if any(w in text for w in NEGATIVE_OLX_WORDS): return False
    if tipo and tipo != "outro": return True
    if area or quartos: return True
    return any(h in text for h in IMOVEL_HINTS)


ESTADO_NOME = {
    "CE":"ceara","SP":"sao-paulo","RJ":"rio-de-janeiro","MG":"minas-gerais",
    "BA":"bahia","RS":"rio-grande-do-sul","PR":"parana","PE":"pernambuco",
    "GO":"goias","DF":"distrito-federal","SC":"santa-catarina","AM":"amazonas",
    "ES":"espirito-santo","PA":"para","MT":"mato-grosso","MS":"mato-grosso-do-sul",
    "MA":"maranhao","PB":"paraiba","RN":"rio-grande-do-norte","AL":"alagoas",
    "PI":"piaui","SE":"sergipe","TO":"tocantins","RO":"rondonia","RR":"roraima","AC":"acre","AP":"amapa",
}


async def _browser(pw):
    b = await pw.chromium.launch(headless=True, args=[
        "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
        "--disable-gpu", "--no-first-run", "--disable-extensions",
    ])
    ctx = await b.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="pt-BR", timezone_id="America/Sao_Paulo", viewport={"width":1366,"height":768},
    )
    await ctx.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,mp4}", lambda r: r.abort())
    await ctx.route("**/(analytics|gtag|hotjar|facebook|doubleclick|criteo|clarity|segment)/**", lambda r: r.abort())
    return b, ctx


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _make_id(prefix: str, link: str) -> str:
    return f"{prefix}_{int(hashlib.md5((link or prefix).encode()).hexdigest()[:12], 16)}"


def _page_range(start=1, max_pages=5):
    if max_pages is None or int(max_pages) <= 0:
        return itertools.count(start)
    return range(start, start + int(max_pages))


async def _zap(ctx, cidade, estado, finalidade, max_pages=5, on_items=None):
    page = await ctx.new_page()
    res  = []
    es   = estado.lower()
    cs   = _slug(cidade)
    tu   = "venda" if finalidade == "venda" else "aluguel"

    for pag in _page_range(1, max_pages):
        url = (f"https://www.zapimoveis.com.br/{tu}/imoveis/{es}+{cs}/"
               + (f"?pagina={pag}" if pag > 1 else ""))
        logger.info(f"[ZAP] p{pag}: {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            logger.warning(f"[ZAP] goto erro: {e}"); break

        try:
            await page.wait_for_selector('[data-cy="rp-property-cd"]', timeout=15000)
        except:
            logger.warning(f"[ZAP] sem cards p{pag}")

        await asyncio.sleep(2)

        cards = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('[data-cy="rp-property-cd"]')).map(card => {
                const title = card.getAttribute('title') || '';
                const price = card.querySelector('[class*="price"],[data-cy="price"],[class*="Price"],[class*="listing-price"]')?.textContent?.trim() || '';
                // Textos dos nós folha (fallback quando não tem title)
                const texts = Array.from(card.querySelectorAll('*'))
                    .map(el => el.children.length === 0 ? el.textContent?.trim() : '')
                    .filter(t => t && t.length > 0);
                const seen = new Set();
                const unique = texts.filter(t => { if(seen.has(t)) return false; seen.add(t); return true; });
                return {
                    title: title,
                    price: price,
                    texts: unique,
                    link:  card.querySelector('a')?.href || '',
                    id:    card.getAttribute('data-id') || card.id || '',
                };
            }).filter(c => c.title || c.price || c.texts.length > 0);
        }""")

        novos = 0
        for c in (cards or []):
            title  = c.get("title","")
            texts  = c.get("texts",[])

            # Preço: do campo price ou dos textos
            preco = _preco(c.get("price",""))
            if not preco:
                for t in texts:
                    preco = _preco(t)
                    if preco: break
            if not preco: continue

            # Se tem title, extrai tudo por regex (mais preciso)
            if title:
                info = _parse_title_zap(title, cidade, estado, finalidade) or {}
            else:
                # Monta info dos textos coletados
                full = " | ".join(texts)
                info = dict(
                    tipo=_tipo(texts[0] if texts else ""),
                    area=None, quartos=None, banheiros=None, vagas=None, bairro="",
                )
                # ZAP/VivaReal: "com 8 m²" ou "8 m²" no texto
                m = re.search(r"(?:com\s+)?([\d]+(?:[,\.][\d]+)?)\s*m²", full, re.I)
                if m:
                    try:
                        v = float(m.group(1).replace(",","."))
                        if v > 5: info["area"] = v
                    except: pass
                m = re.search(r"(\d+)\s*quarto", full, re.I)
                if m: info["quartos"] = int(m.group(1))
                m = re.search(r"(\d+)\s*banheiro", full, re.I)
                if m: info["banheiros"] = int(m.group(1))
                m = re.search(r"(\d+)\s*vaga", full, re.I)
                if m: info["vagas"] = int(m.group(1))
                # ZAP sem title: bairro está depois do último " - "
                # Ex: "Apartamento para comprar - Aldeota"
                for t in texts:
                    if " - " in t:
                        candidato = t.rsplit(" - ", 1)[-1].strip()
                        if (candidato.lower() != cidade.lower()
                                and not RUA_RE.match(candidato)
                                and len(candidato.replace(" ","")) > 2
                                and len(candidato.split()) <= 4):
                            info["bairro"] = candidato
                            break
                # Fallback genérico se não achou pelo " - "
                if not info.get("bairro"):
                    for t in texts:
                        if re.match(r"^R\$", t): continue
                        if re.match(r"^\d", t): continue
                        if t.lower() == cidade.lower(): continue
                        if len(t.replace(" ","")) <= 2: continue
                        if RUA_RE.match(t): continue
                        if any(x in t.lower() for x in ["m²","quarto","banheiro","vaga","suite",
                            "destaque","exclusivo","imperdível","oportunidade","lançamento",
                            "mobiliado","decorado","novo","pronto"]): continue
                        if len(t.split()) > 4: continue
                        info["bairro"] = t; break

            link = c.get("link","")
            uinfo = _url_info(link, cidade, estado)
            if uinfo:
                info.update({k:v for k,v in uinfo.items() if k in {"tipo","bairro","titulo"} and v})
            info["bairro"] = _clean_bairro(info.get("bairro", ""))
            titulo_final = (info.get("titulo") or title or (texts[0] if texts else ""))[:120]
            if titulo_final.lower().strip() in GENERIC_TITLES and uinfo.get("titulo"):
                titulo_final = uinfo["titulo"][:120]
            ei   = c.get("id") or f"zap_dom_{int(hashlib.md5(link.encode()).hexdigest()[:12], 16)}"
            res.append(Imovel(
                external_id=f"zap_{ei}", url=link, site="ZAP Imóveis",
                titulo=titulo_final,
                finalidade=uinfo.get("finalidade", finalidade),
                tipo=info.get("tipo","outro"),
                preco=preco,
                bairro=info.get("bairro",""),
                cidade=cidade, estado=estado,
                area_m2=info.get("area"),
                preco_m2=_calc_preco_m2(preco, info.get("area")),
                quartos=info.get("quartos"),
                banheiros=info.get("banheiros"),
                vagas=info.get("vagas"),
                is_lancamento=uinfo.get("is_lancamento", False),
                data_coleta=_now_iso(),
            ))
            novos += 1

        logger.info(f"[ZAP] p{pag}: {novos}")
        if on_items and novos:
            on_items(res[-novos:])
        if novos == 0: break
        await asyncio.sleep(random.uniform(2.5, 4))

    await page.close()
    logger.info(f"[ZAP] Total {finalidade}: {len(res)}")
    return res


# ══════════════════════════════════════════════════════════════════════════════
# VivaReal — data-cy="rp-property-cd" → texts dentro do container flex
# ══════════════════════════════════════════════════════════════════════════════

async def _vivareal(ctx, cidade, estado, finalidade, max_pages=5, on_items=None):
    page = await ctx.new_page()
    res  = []
    en   = ESTADO_NOME.get(estado.upper(), estado.lower())
    cs   = _slug(cidade)
    tu   = "venda" if finalidade == "venda" else "aluguel"

    for pag in _page_range(1, max_pages):
        url = (f"https://www.vivareal.com.br/{tu}/{en}/{cs}/"
               + (f"?pagina={pag}" if pag > 1 else ""))
        logger.info(f"[VivaReal] p{pag}: {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            logger.warning(f"[VivaReal] goto erro: {e}"); break

        try:
            await page.wait_for_selector('[data-cy="rp-property-cd"]', timeout=15000)
        except:
            logger.warning(f"[VivaReal] sem cards p{pag}")

        await asyncio.sleep(2)

        cards = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('[data-cy="rp-property-cd"]')).map(card => {
                // Acha o container pela propriedade className — @ e / são inválidos em CSS selector
                // classe exata: "flex flex-col grow min-w-0 content-stretch border-neutral-90 @min-2xl/card:border-l pb-2 gap-2 @container/card__container"
                const container = Array.from(card.querySelectorAll('*')).find(el =>
                    typeof el.className === 'string' &&
                    el.className.includes('@min-2xl/card:border-l') &&
                    el.className.includes('grow') &&
                    el.className.includes('flex')
                ) || card;

                const texts = Array.from(container.querySelectorAll('*'))
                    .map(el => el.children.length === 0 ? el.textContent?.trim() : '')
                    .filter(t => t && t.length > 0 && t.length < 300);
                const seen = new Set();
                const unique = texts.filter(t => { if(seen.has(t)) return false; seen.add(t); return true; });

                const wrapper = card.closest('li, article, section') || card.parentElement;
                const link = card.querySelector('a')?.href
                          || wrapper?.querySelector('a')?.href
                          || card.closest('a')?.href || '';

                return {
                    texts: unique,
                    title: card.getAttribute('title') || '',
                    link,
                    id:    card.getAttribute('data-id') || card.id || '',
                };
            }).filter(c => c.texts.length > 0);
        }""")

        novos = 0
        for c in (cards or []):
            texts = c.get("texts", [])
            title = c.get("title","")

            # Preço — primeiro texto que parece preço (R$)
            preco = None
            for t in texts:
                preco = _preco(t)
                if preco: break
            if not preco: continue

            # Se tem title, extrai tudo dele (mais confiável)
            if title:
                info = _parse_title_zap(title, cidade, estado, finalidade) or {}
                bairro   = info.get("bairro","")
                area     = info.get("area")
                quartos  = info.get("quartos")
                banheiros= info.get("banheiros")
                vagas    = info.get("vagas")
                tipo     = info.get("tipo","outro")
            else:
                # Extrai dos textos coletados
                full = " | ".join(texts)
                tipo     = _tipo(texts[0] if texts else "")
                bairro   = ""
                area     = None
                quartos  = None
                banheiros= None
                vagas    = None
                # VivaReal: "com 8 m²" ou "8 m²"
                m = re.search(r"(?:com\s+)?([\d]+(?:[,\.][\d]+)?)\s*m²", full, re.I)
                if m:
                    try:
                        v = float(m.group(1).replace(",","."))
                        if v > 5: area = v
                    except: pass
                m = re.search(r"(\d+)\s*quarto", full, re.I)
                if m: quartos = int(m.group(1))
                m = re.search(r"(\d+)\s*banheiro", full, re.I)
                if m: banheiros = int(m.group(1))
                m = re.search(r"(\d+)\s*vaga", full, re.I)
                if m: vagas = int(m.group(1))
                # VivaReal sem title: procura texto no formato "X, Cidade" ou "X, Cidade, UF"
                # Regra: encontra cidade no texto e pega a parte anterior
                cidade_norm = cidade.strip().lower()
                for t in texts:
                    if "," not in t: continue
                    partes_t = [p.strip() for p in t.split(",")]
                    for i, p in enumerate(partes_t):
                        if p.lower() == cidade_norm and i > 0:
                            candidato = partes_t[i - 1].strip()
                            if not RUA_RE.match(candidato) and len(candidato.replace(" ","")) > 2:
                                bairro = candidato
                            break
                    if bairro: break
                # Fallback genérico se não achou pelo padrão "X, Cidade"
                if not bairro:
                    for t in texts:
                        if re.match(r"^R\$", t): continue
                        if re.match(r"^\d", t): continue
                        if t.lower() == cidade.lower(): continue
                        if len(t.replace(" ","")) <= 2: continue
                        if RUA_RE.match(t): continue
                        if any(x in t.lower() for x in ["m²","quarto","banheiro","vaga","suite","garagem",
                            "destaque","exclusivo","imperdível","oportunidade","lançamento",
                            "mobiliado","decorado","novo","pronto"]): continue
                        if len(t.split()) > 4: continue
                        bairro = t
                        break

            link = c.get("link","")
            uinfo = _url_info(link, cidade, estado)
            if uinfo.get("tipo"): tipo = uinfo["tipo"]
            if uinfo.get("bairro"): bairro = uinfo["bairro"]
            bairro = _clean_bairro(bairro)
            titulo_final = (uinfo.get("titulo") or title or (texts[0] if texts else ""))[:120]
            ei   = c.get("id") or f"vr_dom_{int(hashlib.md5(link.encode()).hexdigest()[:12], 16)}"
            res.append(Imovel(
                external_id=f"vr_{ei}", url=link, site="Viva Real",
                titulo=titulo_final,
                finalidade=uinfo.get("finalidade", finalidade), tipo=tipo, preco=preco,
                bairro=bairro, cidade=cidade, estado=estado,
                area_m2=area, preco_m2=_calc_preco_m2(preco, area),
                quartos=quartos, banheiros=banheiros, vagas=vagas,
                is_lancamento=uinfo.get("is_lancamento", False),
                data_coleta=_now_iso(),
            ))
            novos += 1

        logger.info(f"[VivaReal] p{pag}: {novos}")
        if on_items and novos:
            on_items(res[-novos:])
        if novos == 0: break
        await asyncio.sleep(random.uniform(2.5, 4))

    await page.close()
    logger.info(f"[VivaReal] Total {finalidade}: {len(res)}")
    return res


# ══════════════════════════════════════════════════════════════════════════════
# OLX — class="olx-adcard__content" → textos dos filhos
# ══════════════════════════════════════════════════════════════════════════════

async def _olx(ctx, cidade, estado, finalidade, max_pages=5, search_slug=None, output_cidade=None, start_page=1, on_items=None):
    page = await ctx.new_page()
    res  = []
    seen_links = set()
    es   = estado.lower()
    cs   = _slug(search_slug or cidade)
    cidade_out = output_cidade or cidade

    base_urls = []
    if cidade_out.strip().lower() == "fortaleza" and estado.upper() == "CE" and finalidade == "venda":
        base_urls = [
            ("apartamentos", "https://www.olx.com.br/imoveis/venda/apartamentos/estado-ce/fortaleza-e-regiao"),
            ("casas", "https://www.olx.com.br/imoveis/venda/casas/estado-ce/fortaleza-e-regiao"),
        ]
    else:
        base_urls = [("imoveis", f"https://{es}.olx.com.br/{cs}-e-regiao/imoveis")]

    for categoria, base_url in base_urls:
        if max_pages is None or int(max_pages) <= 0:
            paginas_msg = f"{start_page}-ate esgotar"
        else:
            paginas_msg = f"{start_page}-{start_page + int(max_pages) - 1}"
        logger.info(f"[OLX] categoria={categoria} | paginas={paginas_msg}")
        for pag in _page_range(start_page, max_pages):
            url = base_url + (f"?o={pag}" if pag > 1 else "")
            logger.info(f"[OLX/{categoria}] p{pag}: {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                logger.warning(f"[OLX/{categoria}] goto erro: {e}"); break

            try:
                await page.wait_for_selector('.olx-adcard__content', timeout=15000)
            except:
                logger.warning(f"[OLX/{categoria}] sem cards p{pag}")

            await asyncio.sleep(1.5)

            cards = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.olx-adcard__content')).map(card => {
                const textEls = Array.from(card.querySelectorAll('[class*="text"], [class*="Text"], span, p, h2, h3'));
                const texts = textEls
                    .map(el => el.textContent?.trim() || '')
                    .filter(t => t.length > 0 && t.length < 300);
                const unique = [...new Set(texts)];

                // Localização específica: "Fortaleza, Aldeota" (Cidade, Bairro)
                const locEl = card.querySelector('.typo-caption.olx-adcard__location')
                           || card.querySelector('[class*="adcard__location"]')
                           || card.querySelector('[class*="location"]');
                const locText = locEl ? locEl.textContent?.trim() : '';

                // Area/quartos/banheiros/vagas: a OLX costuma expor esses atributos no aria-label.
                let areaM2 = null;
                let quartos = null;
                let banheiros = null;
                let vagas = null;
                const details = Array.from(card.querySelectorAll('.olx-adcard__detail, [class*="adcard__detail"]'));
                for (const d of details) {
                    const label = (d.getAttribute('aria-label') || '').toLowerCase();
                    if (label.endsWith('metros quadrados')) {
                        const num = parseFloat(label.replace('metros quadrados', '').trim().replace(',', '.'));
                        if (!isNaN(num) && num > 5) areaM2 = num;
                    }
                    let m = label.match(/(\\d+)\\s+quarto/);
                    if (m) quartos = parseInt(m[1], 10);
                    m = label.match(/(\\d+)\\s+banheiro/);
                    if (m) banheiros = parseInt(m[1], 10);
                    m = label.match(/(\\d+)\\s+(vaga|garagem|estacionamento)/);
                    if (m) vagas = parseInt(m[1], 10);
                }

                const wrapper = card.closest('li') || card.parentElement;
                const link = card.querySelector('a')?.href
                          || wrapper?.querySelector('a')?.href || '';
                const id   = wrapper?.getAttribute('data-lurker-id')
                          || wrapper?.getAttribute('data-eid') || '';
                const img = card.querySelector('img') || wrapper?.querySelector('img');
                const imagemUrl = img?.currentSrc || img?.src || img?.getAttribute('data-src') || img?.getAttribute('data-original') || '';

                return { texts: unique, locText, areaM2, quartos, banheiros, vagas, link, id, imagemUrl };
            });
        }""")

            novos = 0
            for c in (cards or []):
                texts = c.get("texts", [])
                full  = " | ".join(texts)

                # Preço
                preco = None
                for t in texts:
                    preco = _preco(t)
                    if preco: break
                if not preco: 
                    continue

                # Tipo — geralmente no título (primeiro texto longo)
                tipo  = "outro"
                for t in texts:
                    if len(t) > 10:
                        tipo = _tipo(t); break

                # OLX: classe "typo-caption olx-adcard__location"
                # Formato real: "Fortaleza, Aldeota" (Cidade, Bairro)
                bairro = ""
                loc_text = c.get("locText", "").strip()
                if loc_text and "," in loc_text:
                    partes = [p.strip() for p in loc_text.split(",", 1)]
                    # Formato "Cidade, Bairro"
                    if partes[0].lower() == cidade.lower() and len(partes) > 1:
                        candidato = partes[1].split("-")[0].strip()
                        if not RUA_RE.match(candidato) and len(candidato.replace(" ","")) > 2:
                            bairro = candidato
                    # Formato invertido "Bairro, Cidade"
                    elif len(partes) > 1 and partes[-1].strip().lower() == cidade.lower():
                        candidato = partes[0].split("-")[0].strip()
                        if not RUA_RE.match(candidato) and len(candidato.replace(" ","")) > 2:
                            bairro = candidato
                # Fallback — percorre textos
                if not bairro:
                    for t in texts:
                        if cidade.lower() in t.lower() and "," in t:
                            partes = [p.strip() for p in t.split(",")]
                            for p in partes:
                                p_c = p.split("-")[0].strip()
                                if p_c.lower() == cidade.lower(): continue
                                if len(p_c.replace(" ","")) <= 2: continue
                                if RUA_RE.match(p_c): continue
                                bairro = p_c; break
                            break
                # Último fallback — URL
                if not bairro:
                    m = re.search(r"olx\.com\.br/([^/?]+)/imoveis", c.get("link",""))
                    if m:
                        sl = m.group(1).replace("-e-regiao","").strip("-")
                        bairro = sl.replace("-"," ").title()
                        if bairro.lower() == cidade.lower(): bairro = ""

                # Área
                # Área: do aria-label capturado no JS, fallback regex no texto
                area = c.get("areaM2")
                if not area:
                    m = re.search(r"([\d]+(?:[,\.][\d]+)?)\s*m²", full)
                    if m:
                        try: area = float(m.group(1).replace(",","."))
                        except: pass

                quartos  = c.get("quartos")
                m = re.search(r"(\d+)\s*quarto", full, re.I)
                if not quartos and m: quartos = int(m.group(1))
                banheiros = c.get("banheiros")
                m = re.search(r"(\d+)\s*banheiro", full, re.I)
                if not banheiros and m: banheiros = int(m.group(1))
                vagas = c.get("vagas")
                m = re.search(r"(\d+)\s*(?:vaga|garagem|estacionamento)", full, re.I)
                if not vagas and m: vagas = int(m.group(1))

                titulo_final = next((t for t in texts if len(t) > 10), "")[:120]
                if not _looks_like_olx_imovel(titulo_final, full, tipo, area, quartos):
                    continue
                # se o título fala aluguel, respeita isso mesmo quando o argumento veio como venda
                finalidade_final = "aluguel" if re.search(r"\balug", titulo_final, re.I) else finalidade
                bairro = _clean_bairro(bairro)
                link = c.get("link","")
                if link and link in seen_links:
                    continue
                if link:
                    seen_links.add(link)
                ei   = c.get("id") or f"olx_dom_{int(hashlib.md5(link.encode()).hexdigest()[:12], 16)}"
                res.append(Imovel(
                    external_id=f"olx_{ei}", url=link, site="OLX",
                    titulo=titulo_final,
                    finalidade=finalidade_final, tipo=tipo, preco=preco,
                    bairro=bairro, cidade=cidade_out, estado=estado,
                    area_m2=area, preco_m2=_calc_preco_m2(preco, area),
                    quartos=quartos, banheiros=banheiros, vagas=vagas,
                    imagem_url=c.get("imagemUrl") or None,
                    data_coleta=_now_iso(),
                ))
                novos += 1

            logger.info(f"[OLX/{categoria}] p{pag}: {novos}")
            if on_items and novos:
                on_items(res[-novos:])
            if novos == 0: break
            await asyncio.sleep(random.uniform(2, 3.5))

    await page.close()
    logger.info(f"[OLX] Total {finalidade}: {len(res)}")
    return res


# ══════════════════════════════════════════════════════════════════════════════
# ImovelWeb — class="postingCardLayout-module__posting-card-container"
#             → textos dentro de class="postingCard-module__posting-top"
# ══════════════════════════════════════════════════════════════════════════════

async def _imovelweb(ctx, cidade, estado, finalidade, max_pages=5, on_items=None):
    page = await ctx.new_page()
    res  = []
    es   = estado.lower()
    cs   = _slug(cidade)
    op   = "imoveis-venda" if finalidade == "venda" else "imoveis-aluguel"

    for pag in _page_range(1, max_pages):
        url = (f"https://www.imovelweb.com.br/{op}-{cs}-{es}.html"
               + (f"?pag={pag}" if pag > 1 else ""))
        logger.info(f"[ImovelWeb] p{pag}: {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            logger.warning(f"[ImovelWeb] goto erro: {e}"); break

        try:
            # Tenta múltiplos seletores — o módulo CSS pode ter hash variável no Render
            await page.wait_for_selector(
                '[class*="posting-card-container"], [class*="postingCardLayout"], [data-qa="posting PROPERTY"], [class*="Posting_"]',
                timeout=15000)
        except:
            logger.warning(f"[ImovelWeb] sem cards p{pag}")
            # Loga o HTML para debug do seletor
            try:
                sample = await page.evaluate(
                    "() => document.querySelectorAll('li, article, section')[2]?.className || 'sem cards'"
                )
                logger.info(f"[ImovelWeb] 3o elemento className: {str(sample)[:120]}")
            except: pass

        await asyncio.sleep(1.5)

        cards = await page.evaluate("""() => {
            // Tenta seletor exato primeiro, depois fallbacks progressivos
            let nodeList = document.querySelectorAll('.postingCardLayout-module__posting-card-container');
            if (!nodeList.length) nodeList = document.querySelectorAll('[class*="posting-card-container"]');
            if (!nodeList.length) nodeList = document.querySelectorAll('[data-qa="posting PROPERTY"]');
            if (!nodeList.length) nodeList = document.querySelectorAll('[class*="postingCardLayout"]');
            return Array.from(nodeList).map(card => {
                const top = card.querySelector('.postingCard-module__posting-top')
                         || card.querySelector('[class*="posting-top"]')
                         || card.querySelector('[class*="postingTop"]')
                         || card;

                // Todos os textos dos elementos folha dentro do top
                const texts = Array.from(top.querySelectorAll('*'))
                    .map(el => {
                        if (el.children.length > 0) return '';
                        return el.textContent?.trim() || '';
                    })
                    .filter(t => t.length > 0);

                const link = card.querySelector('a')?.href || '';
                const id   = card.getAttribute('data-id') || card.getAttribute('data-posting-id') || '';

                // Localização: "Paupina, Fortaleza" — elemento específico de localização
                const locEl = card.querySelector('[class*="location"]')
                           || card.querySelector('[class*="posting-location"]')
                           || card.querySelector('[class*="postingLocation"]');
                const locText = locEl ? locEl.textContent?.trim() : '';

                return { texts, locText, link, id };
            });
        }""")

        novos = 0
        for c in (cards or []):
            texts = c.get("texts", [])
            full  = " | ".join(texts)

            # Preço
            preco = None
            for t in texts:
                preco = _preco(t)
                if preco: break
            if not preco: continue

            # Tipo
            tipo = "outro"
            for t in texts:
                if len(t) > 8:
                    tipo = _tipo(t); break

            # ImovelWeb: "Paupina, Fortaleza" → bairro ANTES da vírgula
            bairro = ""
            loc_text = c.get("locText", "").strip()
            if loc_text and "," in loc_text:
                partes = [p.strip() for p in loc_text.split(",")]
                # Encontra cidade na lista e pega a parte anterior
                cidade_norm = cidade.strip().lower()
                for i, p in enumerate(partes):
                    if p.lower() == cidade_norm and i > 0:
                        candidato = partes[i - 1].strip()
                        if not RUA_RE.match(candidato) and len(candidato.replace(" ","")) > 2:
                            bairro = candidato
                        break
            # Fallback — percorre todos os textos
            if not bairro:
                for t in texts:
                    if "," in t and "R$" not in t and len(t) > 5:
                        partes = [p.strip() for p in t.split(",")]
                        cidade_norm = cidade.strip().lower()
                        for i, p in enumerate(partes):
                            if p.lower() == cidade_norm and i > 0:
                                candidato = partes[i - 1].strip()
                                if not RUA_RE.match(candidato) and len(candidato.replace(" ","")) > 2:
                                    bairro = candidato
                                break
                        if bairro: break

            # Área
            area = None
            m = re.search(r"([\d]+(?:[,\.][\d]+)?)\s*m²", full)
            if m:
                try: area = float(m.group(1).replace(",","."))
                except: pass

            quartos   = None
            m = re.search(r"(\d+)\s*(?:quarto|dorm|suite)", full, re.I)
            if m: quartos = int(m.group(1))

            banheiros = None
            m = re.search(r"(\d+)\s*banheiro", full, re.I)
            if m: banheiros = int(m.group(1))

            vagas = None
            m = re.search(r"(\d+)\s*(?:vaga|garagem)", full, re.I)
            if m: vagas = int(m.group(1))

            link = c.get("link","")
            uinfo = _url_info(link, cidade, estado)
            if uinfo.get("tipo"): tipo = uinfo["tipo"]
            if uinfo.get("bairro"): bairro = uinfo["bairro"]
            bairro = _clean_bairro(bairro)
            titulo_final = (uinfo.get("titulo") or next((t for t in texts if len(t) > 10 and not t.lower().startswith("r$")), ""))[:120]
            ei   = c.get("id") or f"iw_dom_{int(hashlib.md5(link.encode()).hexdigest()[:12], 16)}"
            res.append(Imovel(
                external_id=f"iw_{ei}", url=link, site="ImovelWeb",
                titulo=titulo_final,
                finalidade=uinfo.get("finalidade", finalidade), tipo=tipo, preco=preco,
                bairro=bairro, cidade=cidade, estado=estado,
                area_m2=area, preco_m2=_calc_preco_m2(preco, area),
                quartos=quartos, banheiros=banheiros, vagas=vagas,
                is_lancamento=uinfo.get("is_lancamento", False),
                data_coleta=_now_iso(),
            ))
            novos += 1

        logger.info(f"[ImovelWeb] p{pag}: {novos}")
        if on_items and novos:
            on_items(res[-novos:])
        if novos == 0: break
        await asyncio.sleep(random.uniform(2, 3.5))

    await page.close()
    logger.info(f"[ImovelWeb] Total {finalidade}: {len(res)}")
    return res




# ══════════════════════════════════════════════════════════════════════════════
# DETALHAMENTO: abre a página individual do anúncio
# ══════════════════════════════════════════════════════════════════════════════


def _clean_description(desc: str) -> str:
    desc = re.sub(r"\s+", " ", desc or "").strip(" -:|•")
    # corta lixos comuns dos portais depois da descrição real
    stops = [
        "Anúncio criado", "Anuncio criado", "Segurança em primeiro lugar", "Seguranca em primeiro lugar",
        "Nunca transfira", "Denunciar anúncio", "Denunciar anuncio", "Quem vê primeiro", "Quem ve primeiro",
        "Criar alerta", "Contatar anunciante", "Receber ofertas similares", "Enviar mensagem",
        "Ao clicar", "Perguntas para a imobiliária", "Perguntas para a imobiliaria",
        "mostrar telefone", "WhatsApp", "Telefone", "Creci:", "Carregando...",
    ]
    low = desc.lower()
    cut = len(desc)
    for st in stops:
        i = low.find(st.lower())
        if i >= 0:
            cut = min(cut, i)
    desc = desc[:cut].strip(" -:|•")
    # rejeita pedaços que claramente são apenas CTA/telefone, não descrição do imóvel
    dlow = desc.lower()
    if dlow.startswith("completa") or dlow in {"mostrar", "telefone", "whatsapp"}:
        return ""
    if len(desc) < 80 and any(x in dlow for x in ["telefone", "whatsapp", "creci"]):
        return ""
    return desc[:1200] if len(desc) > 25 else ""


def _clean_address(addr: str) -> str:
    addr = re.sub(r"\s+", " ", addr or "").strip(" -:|•")
    stops = ["Saiba mais", "Valores", "Análise de preço", "Analise de preco", "Venda R$", "Aluguel R$", "Descrição", "Descricao", "Características", "Caracteristicas", "Perguntas para", "Seleciona uma", "Esta disponível", "Estou ansioso"]
    low = addr.lower()
    cut = len(addr)
    for st in stops:
        i = low.find(st.lower())
        if i >= 0:
            cut = min(cut, i)
    addr = addr[:cut].strip(" -:|•")
    # Endereço válido costuma começar por logradouro; aceita também "Bairro, Cidade - UF".
    if not addr or len(addr) < 8:
        return ""
    lixo = ["perguntas", "seleciona", "imobiliária", "imobiliaria", "venha conferir", "ansiosos para", "clique", "telefone", "whatsapp"]
    if any(x in addr.lower() for x in lixo):
        return ""
    if not (RUA_RE.match(addr) or re.search(r",\s*[^,]+\s*-\s*[A-Z]{2}\b", addr)):
        return ""
    return addr[:180]

def _extract_address_number(addr: str) -> Optional[str]:
    addr = re.sub(r"\s+", " ", addr or "").strip()
    if not addr:
        return None
    m = re.search(r"(?:n[ºo]\s*|n[úu]mero\s*)(\d+[a-z]?)\b", addr, re.I)
    if m:
        return m.group(1)
    m = re.search(r",\s*(\d+[a-z]?)\s*$", addr)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d+[a-z]?)\s*$", addr)
    if m:
        return m.group(1)
    return None

def _extract_street(addr: str) -> Optional[str]:
    addr = re.sub(r"\s+", " ", addr or "").strip()
    if not addr:
        return None
    first = addr.split(",", 1)[0].strip()
    return first[:120] if RUA_RE.match(first) else None

def _parse_rating(text: str) -> Optional[float]:
    if text in (None, ""):
        return None
    try:
        v = float(str(text).replace(",", "."))
        return v if 0 <= v <= 5 else None
    except Exception:
        return None

def _extract_features(text: str) -> dict:
    """Extrai atributos estruturados a partir de texto livre do anúncio."""
    raw = re.sub(r"\s+", " ", text or "").strip()
    low = _slug(raw).replace("-", " ")
    out = {}

    def has(*needles):
        return any(n in low for n in needles)

    def int_from_patterns(patterns):
        for pat in patterns:
            m = re.search(pat, raw, re.I)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    continue
        return None

    suites = int_from_patterns([r"(\d+)\s*su[ií]tes?", r"(\d+)\s*suite(s)?"])
    if suites is not None:
        out["suites"] = suites

    andar = 0 if has("terreo", "térreo") else int_from_patterns([
        r"(\d+)\s*andar",
        r"andar\s*(\d+)",
        r"(\d+)\s*o\s*andar",
        r"(\d+)\s*º\s*andar",
        r"(\d+)\s*andar(es)?",
    ])
    if andar is not None:
        out["andar"] = andar

    bool_map = {
        "portaria": ["portaria", "porteiro", "portaria 24", "portaria eletr", "controle de acesso"],
        "vista_mar": ["vista mar", "vista para o mar", "frente mar", "beira mar", "vista para mar"],
        "condominio_fechado": ["condominio fechado", "condomínio fechado", "residencial fechado", "empreendimento fechado"],
        "piscina": ["piscina", "piscinas", "hidromassagem"],
        "deck": ["deck"],
        "varanda_gourmet": ["varanda gourmet", "terraço gourmet", "terraco gourmet"],
        "varanda": ["varanda", "sacada", "terraço", "terraco"],
        "academia": ["academia", "fitness", "gym"],
        "salao_festa": ["salao de festa", "salão de festa", "salao de festas", "salão de festas"],
        "salao_jogos": ["salao de jogos", "salão de jogos", "game room"],
        "quadra_campo": ["quadra", "campo", "quadra poliesportiva", "quadra de futebol", "campo de futebol"],
    }
    for field, needles in bool_map.items():
        value = has(*needles)
        if field == "varanda" and not value:
            value = bool(out.get("varanda_gourmet")) or has("sacada", "terraço", "terraco")
        out[field] = value

    return out

def _first_int(text: str, patterns) -> Optional[int]:
    for pat in patterns:
        m = re.search(pat, text or "", re.I)
        if not m:
            continue
        try:
            return int(m.group(1))
        except Exception:
            continue
    return None

def _first_float(text: str, patterns) -> Optional[float]:
    for pat in patterns:
        m = re.search(pat, text or "", re.I)
        if not m:
            continue
        try:
            value = m.group(1).replace(".", "").replace(",", ".")
            return float(value)
        except Exception:
            continue
    return None

def _parse_detail_text(text: str) -> dict:
    """Extrai descrição, condomínio, IPTU e endereço a partir do texto da página."""
    text = re.sub(r"\s+", " ", text or " ").strip()
    out = {}
    if not text:
        return out

    area = _first_float(text, [
        r"([\d\.]+(?:,\d+)?)\s*m(?:\u00b2|2)\b",
        r"(?:area|\u00e1rea)(?:\s+(?:util|\u00fatil|privativa|total))?\s*([\d\.]+(?:,\d+)?)",
        r"([\d\.]+(?:,\d+)?)\s*m(?:²|Â²|2)\b",
        r"[ÁAÃ]rea(?:\s+útil|\s+privativa|\s+total)?\s*([\d\.]+(?:,\d+)?)",
    ])
    if area and area > 5:
        out["area_m2"] = area

    quartos = _first_int(text, [r"(\d+)\s*(?:quartos?|dormit[oóÃ³]rios?|dorms?)\b"])
    if quartos is not None:
        out["quartos"] = quartos
    banheiros = _first_int(text, [r"(\d+)\s*banheiros?\b"])
    if banheiros is not None:
        out["banheiros"] = banheiros
    vagas = _first_int(text, [r"(\d+)\s*(?:vagas?|garagens?)\b"])
    if vagas is not None:
        out["vagas"] = vagas

    # Condomínio e IPTU. Mantém conservador para evitar confundir preço do imóvel.
    m = re.search(r"Condom[ií]nio\s*(?:R\$)?\s*([\d\.]+)(?:,\d{1,2})?", text, re.I)
    if m:
        try: out["condominio"] = float(m.group(1).replace(".", ""))
        except Exception: pass
    m = re.search(r"IPTU\s*(?:R\$)?\s*([\d\.]+)(?:,\d{1,2})?", text, re.I)
    if m:
        try: out["iptu"] = float(m.group(1).replace(".", ""))
        except Exception: pass

    # Endereço: procura blocos comuns dos portais. Pode vir só bairro/cidade se o site ocultar rua.
    patterns = [
        r"Endere[cç]o\s*(.*?)(?:Descri[cç][aã]o|Caracter[ií]sticas|Condom[ií]nio|IPTU|Mapa|Fale|Contato|$)",
        r"Localiza[cç][aã]o\s*(.*?)(?:Descri[cç][aã]o|Caracter[ií]sticas|Condom[ií]nio|IPTU|Mapa|Fale|Contato|$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            cand = _clean_address(m.group(1))
            if cand:
                out["endereco"] = cand
                out["rua"] = _extract_street(cand)
                out["numero"] = _extract_address_number(cand)
                break

    # Descrição: pega uma janela depois de "Descrição"; fallback para meta description fica no JS.
    m = re.search(r"Descri[cç][aã]o\s*(.*?)(?:Caracter[ií]sticas|Comodidades|Condom[ií]nio|IPTU|Localiza[cç][aã]o|Mapa|Fale|Contato|$)", text, re.I)
    if m:
        desc = _clean_description(m.group(1))
        if desc:
            out["descricao"] = desc
    out.update(_extract_features(text))
    return out


def _apply_detail_fields(item: Imovel, parsed: dict) -> Imovel:
    scalar_fields = [
        "area_m2", "quartos", "banheiros", "vagas", "suites", "andar",
        "condominio", "iptu",
    ]
    for field in scalar_fields:
        if parsed.get(field) is not None:
            setattr(item, field, parsed[field])

    bool_fields = [
        "portaria", "vista_mar", "condominio_fechado", "piscina", "deck",
        "varanda_gourmet", "varanda", "academia", "salao_festa",
        "salao_jogos", "quadra_campo",
    ]
    for field in bool_fields:
        if parsed.get(field) is not None:
            setattr(item, field, parsed[field])

    if parsed.get("descricao") and not item.descricao:
        item.descricao = parsed["descricao"]
    if parsed.get("endereco") and not item.endereco:
        item.endereco = _clean_address(parsed["endereco"])
    if item.endereco and not item.numero_endereco:
        item.numero_endereco = _extract_address_number(item.endereco)
    if item.endereco:
        known_b = _extract_known_bairro(item.endereco)
        if known_b:
            item.bairro = known_b

    item.preco_m2 = _calc_preco_m2(item.preco, item.area_m2)
    return _sanitize_item(item)


async def _detail_one(ctx, item: Imovel, sem: asyncio.Semaphore) -> Imovel:
    if not item.url:
        return item
    async with sem:
        page = await ctx.new_page()
        try:
            await page.goto(item.url, wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(1.2)
            data = await page.evaluate("""() => {
                const meta = document.querySelector('meta[name="description"], meta[property="og:description"]')?.content || '';
                const title = document.querySelector('meta[property="og:title"]')?.content || document.title || '';
                const image = document.querySelector('meta[property="og:image"], meta[name="twitter:image"]')?.content
                    || document.querySelector('img')?.currentSrc
                    || document.querySelector('img')?.src
                    || '';
                const bodyText = document.body ? document.body.innerText : '';
                const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"], script[type="application/json"], script#__NEXT_DATA__'))
                    .map(s => s.textContent || '')
                    .filter(t => t && t.length < 250000);
                return {meta, title, bodyText, scripts};
            }""")
            parsed = _parse_detail_text(data.get("bodyText", ""))
            if data.get("title"):
                title_parsed = _parse_detail_text(data.get("title", ""))
                parsed.update({k: v for k, v in title_parsed.items() if parsed.get(k) in (None, "")})
            meta_desc = _clean_description(data.get("meta", ""))

            # JSON-LD costuma ter description/address em alguns sites.
            for raw in data.get("scripts", []) or []:
                try:
                    obj = json.loads(raw)
                except Exception:
                    continue
                stack = obj if isinstance(obj, list) else [obj]
                while stack:
                    cur = stack.pop()
                    if isinstance(cur, list):
                        stack.extend(cur); continue
                    if not isinstance(cur, dict):
                        continue
                    if not parsed.get("descricao") and isinstance(cur.get("description"), str) and len(cur["description"]) > 30:
                        jd = _clean_description(cur["description"])
                        if jd: parsed["descricao"] = jd
                    for key in ["description", "name", "title"]:
                        val = cur.get(key)
                        if isinstance(val, str):
                            val_parsed = _parse_detail_text(val)
                            parsed.update({k: v for k, v in val_parsed.items() if parsed.get(k) in (None, "")})
                    addr = cur.get("address")
                    if not parsed.get("endereco"):
                        if isinstance(addr, str) and len(addr) > 8:
                            parsed["endereco"] = addr[:180]
                        elif isinstance(addr, dict):
                            vals = [addr.get(k) for k in ["streetAddress", "addressLocality", "addressRegion"] if addr.get(k)]
                            if vals: parsed["endereco"] = ", ".join(vals)[:180]
                    for src, dest in [
                        ("floorSize", "area_m2"),
                        ("numberOfRooms", "quartos"),
                        ("numberOfBedrooms", "quartos"),
                        ("numberOfBathroomsTotal", "banheiros"),
                    ]:
                        val = cur.get(src)
                        if isinstance(val, dict):
                            val = val.get("value")
                        if val is not None and parsed.get(dest) is None:
                            try:
                                parsed[dest] = float(val) if dest == "area_m2" else int(val)
                            except Exception:
                                pass
                    for v in cur.values():
                        if isinstance(v, (dict, list)):
                            stack.append(v)

            if meta_desc and not parsed.get("descricao"):
                parsed["descricao"] = meta_desc
            if parsed.get("endereco") and not item.endereco:
                item.endereco = _clean_address(parsed["endereco"])
            if item.endereco:
                item.rua = item.rua or _extract_street(item.endereco)
                item.numero = item.numero or item.numero_endereco or _extract_address_number(item.endereco)
                item.numero_endereco = item.numero_endereco or item.numero
            if item.endereco:
                # Se o endereço detalhado contém um bairro conhecido, usa-o para corrigir bairro quebrado
                known_b = _extract_known_bairro(item.endereco)
                if known_b:
                    item.bairro = known_b
            if parsed.get("rua") and not item.rua:
                item.rua = parsed["rua"]
            if parsed.get("numero") and not item.numero:
                item.numero = parsed["numero"]
                item.numero_endereco = item.numero_endereco or item.numero
            if parsed.get("anuncio_criado") and not item.anuncio_criado:
                item.anuncio_criado = parsed["anuncio_criado"]
            if parsed.get("corretora") and not item.corretora:
                item.corretora = parsed["corretora"]
            if parsed.get("nota_media") is not None and item.nota_media is None:
                item.nota_media = parsed["nota_media"]
            if data.get("image") and not item.imagem_url:
                item.imagem_url = data["image"]
            if parsed.get("condominio") is not None:
                item.condominio = parsed["condominio"]
            if parsed.get("iptu") is not None:
                item.iptu = parsed["iptu"]
            _apply_detail_fields(item, parsed)
        except Exception as e:
            logger.debug(f"[detalhe] falhou {item.url}: {e}")
        finally:
            await page.close()
        await asyncio.sleep(random.uniform(0.4, 0.9))
        return item


async def enrich_details(ctx, items, max_items=30, concurrency=2, on_items=None):
    alvo = [iv for iv in items if iv.url]
    if max_items is not None and int(max_items) > 0:
        alvo = alvo[:int(max_items)]
    if not alvo:
        return items
    logger.info(f"[detalhe] abrindo até {len(alvo)} anúncios individuais...")
    sem = asyncio.Semaphore(max(1, int(concurrency)))
    tasks = [asyncio.create_task(_detail_one(ctx, iv, sem)) for iv in alvo]
    for task in asyncio.as_completed(tasks):
        enriched = await task
        if on_items:
            on_items([enriched])
    return items



def _property_signature(iv: Imovel):
    """Chave frouxa para remover o mesmo imóvel publicado em portais diferentes."""
    bairro = _slug(iv.bairro or "")
    tipo = iv.tipo or ""
    area = round(float(iv.area_m2 or 0)) if iv.area_m2 else 0
    preco = round(float(iv.preco or 0) / 1000) * 1000 if iv.preco else 0
    q = iv.quartos or 0
    b = iv.banheiros or 0
    v = iv.vagas or 0
    if not bairro or not preco or not area:
        return None
    return (bairro, tipo, area, preco, q, b, v, iv.finalidade)


def _quality_score(iv: Imovel) -> int:
    score = 0
    # Preferir portais que geralmente entregam detalhe melhor
    if iv.site == "ZAP Imóveis": score += 8
    elif iv.site == "Viva Real": score += 7
    elif iv.site == "ImovelWeb": score += 5
    if iv.url: score += 5
    if iv.tipo and iv.tipo != "outro": score += 4
    if iv.bairro: score += 4
    if iv.area_m2: score += 3
    if iv.quartos is not None: score += 2
    if iv.banheiros is not None: score += 2
    if iv.vagas is not None: score += 1
    if iv.endereco: score += 5
    if iv.descricao: score += 4
    if iv.condominio is not None: score += 2
    if iv.iptu is not None: score += 2
    # Penalidades para registros suspeitos
    if iv.quartos and iv.quartos > 10 and iv.area_m2 and iv.area_m2 < 120: score -= 10
    if iv.tipo == "outro": score -= 3
    if iv.preco_m2 and (iv.preco_m2 < 50 or iv.preco_m2 > 50000): score -= 4
    return score


def _sanitize_item(iv: Imovel) -> Imovel:
    # Título limpo e sem extensão .html.
    if iv.titulo:
        iv.titulo = re.sub(r"\.html$", "", iv.titulo, flags=re.I).strip()
        iv.titulo = re.sub(r"\s+", " ", iv.titulo)[:120]

    # Limpa campos textuais primeiro.
    if iv.endereco:
        iv.endereco = _clean_address(iv.endereco)
        if not iv.numero_endereco:
            iv.numero_endereco = _extract_address_number(iv.endereco)
        if not iv.numero:
            iv.numero = iv.numero_endereco or _extract_address_number(iv.endereco)
        if not iv.rua:
            iv.rua = _extract_street(iv.endereco)
    elif iv.rua:
        iv.rua = re.sub(r"\s+", " ", iv.rua).strip()[:120]
    if not iv.numero_endereco and iv.numero:
        iv.numero_endereco = iv.numero
    if not iv.numero and iv.numero_endereco:
        iv.numero = iv.numero_endereco
    if iv.descricao:
        iv.descricao = _clean_description(iv.descricao)

    feature_text = " ".join([
        iv.titulo or "",
        iv.descricao or "",
        iv.endereco or "",
        iv.url or "",
    ])
    feats = _extract_features(feature_text)
    for k, v in feats.items():
        if getattr(iv, k, None) in (None, ""):
            setattr(iv, k, v)

    # Bairro: usa URL + endereço + título + bairro original; endereço/URL têm prioridade prática.
    uinfo = _url_info(iv.url, iv.cidade, iv.estado) if iv.url else {}
    candidates = [uinfo.get("bairro", ""), iv.endereco or "", iv.bairro or "", iv.titulo or "", iv.url or ""]
    best = _best_bairro(*candidates)
    iv.bairro = best or _clean_bairro(iv.bairro)

    # Normaliza tipo com base em URL/título/atributos.
    if uinfo.get("tipo"):
        iv.tipo = uinfo["tipo"]
    iv.tipo = _force_consistent_tipo(iv)

    # Valores fora da escala usual atrapalham BI; remove o campo em vez de inventar correção.
    if iv.area_m2 and (iv.area_m2 <= 5 or iv.area_m2 > 50000):
        iv.area_m2 = None
    if iv.quartos and iv.quartos > 30:
        iv.quartos = None
    if iv.banheiros and iv.banheiros > 20:
        iv.banheiros = None
    if iv.vagas and iv.vagas > 20:
        iv.vagas = None

    # Se ainda ficou comercial mas tem quartos e não há palavra comercial forte, rebaixa para residencial genérico.
    txt = _slug(" ".join([iv.titulo or "", iv.url or "", iv.descricao or ""])).replace('-', ' ')
    if iv.tipo == "comercial" and iv.quartos and not any(w in txt for w in _COMMERCIAL_WORDS):
        iv.tipo = "apartamento"

    iv.preco_m2 = _calc_preco_m2(iv.preco, iv.area_m2)
    return iv

def _filter_quality(items, include_lancamentos=False, include_sem_url=False):
    # 1) saneia e remove registros que prejudicam consistência.
    candidates = []
    for iv in items:
        if not include_sem_url and not iv.url:
            continue
        if not include_lancamentos and iv.is_lancamento:
            continue
        iv = _sanitize_item(iv)
        if not _is_valid_record(iv):
            continue
        candidates.append(iv)

    # 2) dedup por URL exata.
    by_url = {}
    for iv in candidates:
        key = (iv.url or iv.external_id or "").strip()
        prev = by_url.get(key)
        if prev is None:
            by_url[key] = iv
        else:
            best, other = (iv, prev) if _quality_score(iv) > _quality_score(prev) else (prev, iv)
            by_url[key] = _merge_items(best, other)

    # 3) dedup por ID público do anúncio (muitos ZAP/VivaReal compartilham o mesmo id-XXXXXXXXXX).
    by_public_id = {}
    no_public_id = []
    for iv in by_url.values():
        pid = _listing_id(iv.url)
        if not pid:
            no_public_id.append(iv)
            continue
        prev = by_public_id.get(pid)
        if prev is None:
            by_public_id[pid] = iv
        else:
            best, other = (iv, prev) if _quality_score(iv) > _quality_score(prev) else (prev, iv)
            by_public_id[pid] = _merge_items(best, other)

    # 4) dedup por assinatura frouxa, quando os atributos batem.
    by_sig = {}
    no_sig = []
    for iv in list(by_public_id.values()) + no_public_id:
        sig = _property_signature(iv)
        if not sig:
            no_sig.append(iv)
            continue
        prev = by_sig.get(sig)
        if prev is None:
            by_sig[sig] = iv
        else:
            best, other = (iv, prev) if _quality_score(iv) > _quality_score(prev) else (prev, iv)
            by_sig[sig] = _merge_items(best, other)

    cleaned = [_sanitize_item(x) for x in (list(by_sig.values()) + no_sig)]
    cleaned = [x for x in cleaned if _is_valid_record(x)]
    cleaned.sort(key=lambda x: (x.bairro or "", x.tipo or "", x.preco or 0, x.site))
    return cleaned

def geocode_items(items, user_agent="imov-scraper-only", delay=1.1):
    """Geocodifica bairro/cidade usando Nominatim. Requer internet e respeita pausa entre chamadas."""
    try:
        import requests
    except Exception:
        logger.warning("[geo] instale requests para geocodificação: pip install requests")
        return items
    cache = {}
    for iv in items:
        if not iv.bairro or (iv.latitude and iv.longitude):
            continue
        q = f"{iv.bairro}, {iv.cidade}, {iv.estado}, Brasil"
        if q in cache:
            latlon = cache[q]
        else:
            try:
                r = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": q, "format": "json", "limit": 1},
                    headers={"User-Agent": user_agent},
                    timeout=20,
                )
                data = r.json() if r.ok else []
                latlon = (float(data[0]["lat"]), float(data[0]["lon"])) if data else (None, None)
            except Exception:
                latlon = (None, None)
            cache[q] = latlon
            time.sleep(delay)
        iv.latitude, iv.longitude = latlon
    return items


# ══════════════════════════════════════════════════════════════════════════════
# ORQUESTRADOR
# ══════════════════════════════════════════════════════════════════════════════

async def scrape(cidade, estado, finalidades=("venda", "aluguel"), sites=("olx", "zap", "vivareal", "imovelweb"), detalhar=False, max_detalhes=30, include_lancamentos=False, include_sem_url=False, geocode=False, max_pages=5, sweep_bairros=False, olx_start_page=1, skip_quality_filter=False, on_items=None, detail_concurrency=2):
    """Coleta imóveis usando Playwright e retorna lista de Imovel.

    detalhar=True abre páginas individuais para tentar extrair descrição, endereço, condomínio e IPTU.
    include_lancamentos=False remove /lancamentos/ por padrão, pois costumam vir com construtora no lugar de bairro.
    include_sem_url=False remove registros sem URL.
    geocode=True consulta Nominatim para preencher latitude/longitude por bairro.
    """
    from playwright.async_api import async_playwright
    finalidades = [f.lower() for f in finalidades]
    sites = [s.lower() for s in sites]
    logger.info(f"=== Scraping: {cidade}/{estado} | sites={sites} | finalidades={finalidades} ===")
    all_res = []
    listing_on_items = None if detalhar else on_items

    async with async_playwright() as pw:
        browser, ctx = await _browser(pw)
        try:
            available = {
                "olx": ("OLX", _olx),
                "zap": ("ZAP", _zap),
                "vivareal": ("VivaReal", _vivareal),
                "imovelweb": ("ImovelWeb", _imovelweb),
            }
            selected = [(name, fn) for key, (name, fn) in available.items() if key in sites]
            for fin in finalidades:
                if fin not in {"venda", "aluguel"}:
                    logger.warning(f"Finalidade ignorada: {fin}")
                    continue
                logger.info(f"\n--- {fin.upper()} ---")
                results = await asyncio.gather(
                    *[fn(ctx, cidade, estado, fin, max_pages=max_pages, start_page=olx_start_page, on_items=listing_on_items) if name == "OLX" else fn(ctx, cidade, estado, fin, max_pages=max_pages, on_items=listing_on_items) for name, fn in selected],
                    return_exceptions=True,
                )
                for (site_name, _), r in zip(selected, results):
                    if isinstance(r, Exception):
                        logger.error(f"[{site_name}] Falhou: {r}")
                    else:
                        all_res.extend(r)
                        logger.info(f"[{site_name}/{fin}] {len(r)} coletados")

                if sweep_bairros and cidade.strip().lower() == "fortaleza" and estado.upper() == "CE":
                    # Fortaleza tem estoque muito maior quando a busca é aberta por bairros.
                    for bairro in sorted(BAIRROS_FORTALEZA):
                        if bairro.lower() in {"fortaleza"}:
                            continue
                        try:
                            bairros_res = await _olx(
                                ctx,
                                cidade,
                                estado,
                                fin,
                                max_pages=max_pages,
                                search_slug=bairro,
                                output_cidade=cidade,
                                start_page=olx_start_page,
                                on_items=listing_on_items,
                            )
                            all_res.extend(bairros_res)
                            logger.info(f"[OLX/{fin}] bairro={bairro} {len(bairros_res)} coletados")
                        except Exception as e:
                            logger.error(f"[OLX] bairro={bairro} falhou: {e}")
        finally:
            await browser.close()

    unique = all_res if skip_quality_filter else _filter_quality(all_res, include_lancamentos=include_lancamentos, include_sem_url=include_sem_url)

    if detalhar:
        sem_url = len([iv for iv in unique if not iv.url])
        if sem_url:
            logger.info(f"[detalhe] ignorando {sem_url} registros sem URL; nao e possivel abrir pagina individual")
        # Reabre um browser/contexto só para detalhes, evitando misturar páginas abertas da listagem.
        async with async_playwright() as pw2:
            browser2, ctx2 = await _browser(pw2)
            try:
                await enrich_details(ctx2, unique, max_items=max_detalhes, concurrency=detail_concurrency, on_items=on_items)
            finally:
                await browser2.close()
        # Sanitiza novamente após preencher descrição/endereço/IPTU/condomínio.
        unique = unique if skip_quality_filter else _filter_quality(unique, include_lancamentos=include_lancamentos, include_sem_url=include_sem_url)

    if geocode:
        geocode_items(unique)

    with_b = [iv for iv in unique if iv.bairro]
    logger.info(f"\n=== TOTAL: {len(unique)} únicos | com bairro: {len(with_b)} | sem: {len(unique)-len(with_b)} ===")

    if with_b:
        ex = with_b[0]
        logger.info(f"EXEMPLO: site={ex.site} finalidade={ex.finalidade} tipo={ex.tipo} preco=R${ex.preco:,.0f} bairro={ex.bairro!r} area={ex.area_m2}m² quartos={ex.quartos} banheiros={ex.banheiros} vagas={ex.vagas}")

    return unique




def scrape_sync(cidade, estado, finalidades=("venda", "aluguel"), sites=("olx", "zap", "vivareal", "imovelweb"), **kwargs):
    return asyncio.run(scrape(cidade, estado, finalidades=finalidades, sites=sites, **kwargs))

def to_dicts(imoveis):
    from dataclasses import asdict
    return [asdict(iv) for iv in imoveis]
