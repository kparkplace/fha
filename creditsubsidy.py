"""
Minimal creditsubsidy parser: produces combined_df
"""

import io, re, urllib.request
import pandas as pd

DEFAULT_URL = "https://www.whitehouse.gov/wp-content/uploads/2026/04/cr_supp_fy2027.xlsx"
url = DEFAULT_URL

resp = urllib.request.urlopen(url)
raw = resp.read()
bio = io.BytesIO(raw)
xls = pd.ExcelFile(bio)

# --- Table8 ---
sheet8 = 'Table8' if 'Table8' in xls.sheet_names else next((n for n in xls.sheet_names if 'table8' in n.lower().replace(' ','')), xls.sheet_names[0])
bio.seek(0)
df8 = pd.read_excel(bio, sheet_name=sheet8, header=None, dtype=str)

hdr_idx = 3
if hdr_idx >= len(df8):
    raise ValueError(f"Sheet '{sheet8}' does not contain row {hdr_idx+1} for headers")
field_labels = [str(x).strip() if x is not None else '' for x in df8.iloc[hdr_idx].tolist()]

mmif = next((i for i in range(len(df8)) if any(isinstance(c,str) and 'mmi fund' in c.lower() for c in df8.iloc[i].astype(str).tolist())), None)
if mmif is None:
    raise ValueError(f"Could not find 'MMI Fund' in sheet {sheet8}")

collected = []
for i in range(mmif+1, len(df8)):
    row_vals = df8.iloc[i].astype(str).tolist()
    if any('mmi hecm' in str(c).lower() for c in row_vals):
        break
    first = str(df8.iat[i,0]).strip() if df8.shape[1] > 0 else ''
    if first.upper().startswith('FY'):
        vals = [v.strip() if isinstance(v, str) else v for v in df8.iloc[i].tolist()]
        collected.append(vals)

if not collected:
    raise ValueError("No 'FY' rows found after 'MMI Fund' in Table8")

col_count = df8.shape[1]
norm = [row + [None] * (col_count - len(row)) if len(row) < col_count else row[:col_count] for row in collected]
t8 = pd.DataFrame(norm)

for c in t8.columns[1:]:
    t8[c] = pd.to_numeric(t8[c].astype(str).str.replace(',', ''), errors='coerce')

cleaned = []
for lab in field_labels:
    s = str(lab).replace('\n', '_').replace(' ', '_')
    while '__' in s:
        s = s.replace('__', '_')
    s = s.strip('_')
    cleaned.append(s if s else 'col')

labels_padded = cleaned[:col_count] if len(cleaned) >= col_count else cleaned + [f'col_{i}' for i in range(len(cleaned), col_count)]

t8.columns = labels_padded
t8 = t8.rename(columns={t8.columns[0]: 'fiscal_year'})

for r in range(len(t8)):
    v = t8.iat[r, 0]
    ds = ''.join(re.findall(r"\d+", str(v))) if v is not None else ''
    t8.iat[r, 0] = int(ds) if ds else None

orig_pat = re.compile(r'original.*subsidy.*rate|subsidy.*rate', re.I)
curr_pat = re.compile(r'current.*re-?estimated.*rate|re-?estimated.*rate|current.*rate', re.I)
found_orig = None
found_curr = None
for c in t8.columns:
    if found_orig is None and orig_pat.search(c):
        found_orig = c
    if found_curr is None and curr_pat.search(c):
        found_curr = c

if found_orig is None:
    for c in t8.columns:
        low = c.lower()
        if 'subsid' in low and 'rate' in low:
            found_orig = c
            break
if found_curr is None:
    for c in t8.columns:
        low = c.lower()
        if 'estim' in low and 'rate' in low:
            found_curr = c
            break

if not found_orig or not found_curr:
    raise ValueError(f"Could not locate subsidy rate columns in Table8. Available: {list(t8.columns)}")

t8 = t8[['fiscal_year', found_orig, found_curr]].copy()
t8 = t8.rename(columns={found_orig: 'original_subsidy_rate', found_curr: 'current_reestimated_rate'})

# --- Table2 ---
sheet2 = 'Table2' if 'Table2' in xls.sheet_names else next((n for n in xls.sheet_names if 'table2' in n.lower().replace(' ','')), None)
if sheet2 is None:
    df2 = pd.DataFrame(columns=['fiscal_year', 'original_subsidy_rate', 'current_reestimated_rate'])
else:
    bio.seek(0)
    df2raw = pd.read_excel(bio, sheet_name=sheet2, header=None, dtype=str)
    mmif2 = next((i for i in range(len(df2raw)) if any('mmi fund' in str(c).lower() for c in df2raw.iloc[i].astype(str).tolist())), None)
    rows = []
    if mmif2 is not None:
        candidates = [5, 2]
        def to_num(v):
            if v is None:
                return None
            s = str(v).strip()
            if s == '':
                return None
            neg = False
            if s.startswith('(') and s.endswith(')'):
                neg = True
                s = s[1:-1].strip()
            s = s.replace(',', '').replace('%', '')
            m = re.search(r'-?\d+\.?\d*', s)
            if not m:
                return None
            val = float(m.group(0))
            return -val if neg else val
        for ci in candidates:
            if ci >= df2raw.shape[1]:
                continue
            val = None
            for offset in range(0, 11):
                for r in (mmif2 + offset, mmif2 - offset) if offset > 0 else (mmif2,):
                    if 0 <= r < len(df2raw):
                        n = to_num(df2raw.iat[r, ci])
                        if n is not None:
                            val = n
                            break
                if val is not None:
                    break
            if val is None:
                continue
            fy_cell = None
            for r in (2, 3, 0, 1):
                if 0 <= r < len(df2raw):
                    cval = df2raw.iat[r, ci]
                    if cval and re.search(r'\d{4}', str(cval)):
                        fy_cell = ''.join(re.findall(r'\d+', str(cval)))
                        break
            if fy_cell:
                rows.append({'fiscal_year': int(fy_cell), 'original_subsidy_rate': val, 'current_reestimated_rate': None})
    df2 = pd.DataFrame(rows) if rows else pd.DataFrame(columns=['fiscal_year', 'original_subsidy_rate', 'current_reestimated_rate'])

# --- Combine ---
for c in ['fiscal_year', 'original_subsidy_rate', 'current_reestimated_rate']:
    if c not in t8.columns:
        t8[c] = None

t8_sel = t8[['fiscal_year', 'original_subsidy_rate', 'current_reestimated_rate']].copy()
combined_df = pd.concat([t8_sel, df2], ignore_index=True)
combined_df = combined_df[combined_df['fiscal_year'].notnull()].copy()
combined_df['fiscal_year'] = combined_df['fiscal_year'].astype(int)
combined_df = combined_df.sort_values('fiscal_year').drop_duplicates(subset=['fiscal_year'], keep='first').reset_index(drop=True)

# combined_df is exposed at module level
#%%
# --- Plot (plotnine only): bar chart of current_reestimated_rate with short horizontal light-blue markers for original_subsidy_rate ---
try:
    from plotnine import ggplot, aes, geom_col, geom_segment, labs, theme_classic, theme, element_text, scale_x_continuous
    _USE_PLOTNINE = True
except Exception:
    _USE_PLOTNINE = False

_plot_df = combined_df.sort_values('fiscal_year').copy()
_plot_df = _plot_df[_plot_df['current_reestimated_rate'].notnull()].copy().reset_index(drop=True)
_plot_df['fy_str'] = _plot_df['fiscal_year'].astype(int).astype(str)
_plot_df['_x'] = _plot_df.index.astype(float)

if not _USE_PLOTNINE:
    combined_plot = None
else:
    # short horizontal half-width in x-units
    _hw = 0.2
    _marks = _plot_df[_plot_df['original_subsidy_rate'].notnull()].copy()
    _marks['_x_min'] = _marks['_x'] - _hw
    _marks['_x_max'] = _marks['_x'] + _hw

    p = (
        ggplot(_plot_df, aes(x='_x', y='current_reestimated_rate'))
        + geom_col(fill="#4c72b0")
        + geom_segment(data=_marks, mapping=aes(x='_x_min', xend='_x_max', y='original_subsidy_rate', yend='original_subsidy_rate'), color="#add8e6", size=1.25)
        + scale_x_continuous(breaks=_plot_df['_x'].tolist(), labels=_plot_df['fy_str'].tolist())
        + labs(x='Fiscal Year', y='Current Reestimated Rate', title='Current reestimated rate with original subsidy markers')
        + theme_classic()
        + theme(axis_text_x=element_text(rotation=45, hjust=1))
    )
    combined_plot = p
p
# %%
