<div align="center">

<img src="frontend/iconos/icono-128.png" width="104" alt="AnoniPRO">

# AnoniPRO

**Anonymise any document without your data ever leaving your computer.**

Medical reports · Legal filings · Payroll and contracts · Invoices · Personal paperwork

*Nodo Local — Dr José Ramón Alberto Alonso*

[Versión en español](README.md)

</div>

---

## What it does

You upload a document, AnoniPRO **shows you** every piece of personal data it
found, **you review and confirm**, and you download a copy with that data
**genuinely deleted** from the file.

It does not cover data with a black box: it **removes** it. It cannot be
recovered by copying, pasting or deleting the mark.

**Everything happens on your machine.** No internet, no accounts, nothing sent
anywhere. Documents are never even written to disk: they are processed in memory
and wiped automatically.

| Accepts | Detects | Languages |
|---|---|---|
| PDF, scanned PDF, Word (.docx), Excel (.xlsx), images (JPG, PNG, TIFF) | 29 kinds of personal data, grouped into 8 profiles | Spanish and English (UK and US), with each document's language detected automatically |

> **Note on languages.** The interface is fully bilingual and detection now works
> in both languages: AnoniPRO detects each document's language and applies the
> right engine. Spanish documents get the Spanish identifiers (national ID, social
> security, health card…); English documents get the **UK and US** ones (NHS
> number, National Insurance, SSN/ITIN, postcodes and phone numbers). Other
> languages are not supported.

---

## Install

### 🖥️ On your own computer — the simplest way

1. Unzip `AnoniPRO-portable-mac.zip`.
2. Double-click **`AnoniPRO`** (on Windows, `AnoniPRO.exe`).
3. Your browser opens by itself. That's it.

Nothing is installed and no administrator rights are needed.

> **On macOS**, the system will warn that the app "is damaged" — it is not: it
> simply is not signed by Apple. Inside the folder there is a file called
> **«PRIMERA VEZ — Abrir aquí»**: **right-click** it → **Open**. If the warning
> persists, go to *System Settings → Privacy & Security* and press **"Open
> anyway"**. First time only.

### 🌐 On a server or NAS — for a whole team

Every computer on the network uses it from the browser, **with nothing installed
on them**. Ideal for practices and offices with locked-down machines.

👉 Step by step: **[docs/INSTALAR-EN-NAS.md](docs/INSTALAR-EN-NAS.md)** (Spanish)

### 🛠️ From source

**[docs/PARA-DESARROLLADORES.md](docs/PARA-DESARROLLADORES.md)** (Spanish)

---

## How to use it

1. **Drag** the document onto the window (several, or a whole folder, also work).
2. Pick a **profile** on the left panel for that kind of document.
3. **Review** the list on the right: every item found is highlighted on the
   document. Untick anything you want to keep, and add by hand anything missed.
4. Press **Apply redaction** and confirm.
5. **Download** the anonymised document. AnoniPRO checks it again and warns you
   if anything is left.

Nothing is deleted without your confirmation.

---

## Profiles

| Profile | For | Protects, on top of names, ID, address, phone and e-mail |
|---|---|---|
| **Clinical document** | Records and reports | Health card, medical record and episode numbers, social security and dates (including specimen collection date) |
| **Scientific publication** | Papers, conferences | The above **plus** hospital, department, doctors, registration numbers and dates |
| **Teaching** | Teaching material | As above, keeping the structure of the case |
| **Legal** | Contracts, filings, notary | Case files, court records, deeds, land registry, number plates, IBAN, company tax ID |
| **Company and HR** | Payroll, employment contracts | Social security, IBAN, company tax ID, employee numbers, plates |
| **Invoices and accounting** | Invoices, quotes | Tax IDs, IBAN, cards, invoice numbers and client details |
| **Personal document** | Your own paperwork | IBAN, cards, social security, number plate, land registry |
| **Everything on** | Maximum protection | Absolutely everything |

Identifiers that carry a check digit (**national ID, social security, IBAN,
company tax ID, payment cards**) are **verified mathematically**: if the check
fails, they are not flagged. That avoids marking numbers that merely look alike.

**You can also** shift every date by the same random number of days (preserving
order and intervals without revealing the real ones), replace exact ages with
age bands, and download an **audit report** of what was redacted and with which
settings — never including the original data.

---

## Why it is private

- **Nothing leaves your machine.** No part of the program connects to the
  internet. Unplug the network and it still works.
- **Nothing is written to disk.** Documents live in memory and are wiped after
  30 minutes, or when you press *Finish*.
- **Deletion is real.** In PDFs the text is removed from the content layer; in
  scans and images the pixels are erased; in Word it is replaced inside the
  file; in Excel the relevant cell values are replaced. Compatible hidden
  properties, comments, deleted revisions, external links and metadata are
  removed too. Downloads use a generic filename so a patient name or record
  number in the original filename is not copied to the result.
- **It is checked twice.** After redacting, the resulting document is analysed
  again to make sure nothing survived.

---

## How it finds the data

| Layer | What it is |
|---|---|
| **1 · Rules** | Spanish patterns with check-digit validation: national ID, social security, IBAN, company tax ID, cards, health card, phones, land registry, number plates… |
| **2 · Name model** | A Spanish language model that recognises people, places and organisations with no fixed format. Runs on CPU. |
| **3 · Local AI** *(optional)* | An AI model running **on your own network** (Ollama or LM Studio) for indirect mentions and unusual names. Can be switched on and off; everything works without it. |

Scanned documents and images first go through optical character recognition
(OCR) on your own machine.

---

## Current limitations

- **Old `.doc` files** (Word 97-2003) are not supported — save them as `.docx`.
- **Excel support is `.xlsx` without macros.** Save old `.xls` and macro-enabled
  `.xlsm` files as `.xlsx`. Hidden sheets/cells, tab names and print headers and
  footers are reviewed; comments and links are removed. Formulae, embedded
  objects and complex formatting may change, so review the resulting workbook
  both visually and functionally.
- **OCR is not perfect.** On scans it can misread data, especially e-mail
  addresses. Review the result and use manual marking where needed.
- **Two languages only: Spanish and English** (UK/US), detected automatically
  per document. Other languages are not supported.
- **Always review before sharing.** No automatic tool is infallible: AnoniPRO
  shows you what it found precisely so the final decision is yours.

---

## Licence and components

The AnoniPRO source code is the author's work; **all rights reserved**.

It uses third-party open-source components, owned by their respective authors:
FastAPI, Microsoft Presidio, spaCy, PyMuPDF (AGPL-3.0), python-docx, openpyxl, Tesseract
OCR, Pillow and PDF.js. Language and AI models are distributed under their own
licences.

---

<div align="center">
<sub>AnoniPRO · Nodo Local · 100% local processing, works offline</sub>
</div>
