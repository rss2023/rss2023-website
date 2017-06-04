"""
Script for cleaning paper CSV file.
Script for generating individual paper pages.
Script for extracting camera-ready submissions and preparing them for GCS.

NOTE: raw_papers.txt must be generated by exporting from Excel in "UTF-16 Unicode Text (.txt)".
This resolves an assortment of encoding issues for Latin-1 characters.

python3 _data/scripts/papers.py raw_papers.txt _data/papers.csv _program/papers --submdir _papers
"""

import argparse
import codecs
import csv
import os
import shutil

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('tsv_infile', help='Excel-exported paper data')
    parser.add_argument('csv_outfile', help='Path to CSV file')
    parser.add_argument('outdir', help='Directory for output paper pages')
    parser.add_argument('--submdir', help='Directory of unzipped camera-ready submissions')
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # Read raw paper information
    with codecs.open(args.tsv_infile, 'r', 'utf16') as f:
        reader = csv.DictReader(f, delimiter='\t')
        raw_paper_data = sorted(reader,
            key=lambda d: d['Paper Title'].replace('(', '').lower())

    # Generate paper CSV and pages
    with open(args.csv_outfile, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'session_id', 'external_id', 'internal_id',
            'title', 'abstract', 'authors', 'areas'])

        writer.writeheader()
        for i, raw_paper in enumerate(raw_paper_data, 1):
            abstract = raw_paper['Abstract'].encode('ascii', 'xmlcharrefreplace').decode()
            authors = ', '.join([
                ' '.join(author.split(',')[0].replace('*', '').split())
                for author in raw_paper['Author Names'].encode('ascii', 'xmlcharrefreplace').decode().split('; ')
            ])

            internal_id = raw_paper['Paper ID']
            external_id = '{:0>2}'.format(i)

            paper = {
                'session_id': 0,
                'external_id': external_id,
                'internal_id': internal_id,
                'title': raw_paper['Paper Title'],
                'abstract': abstract,
                'authors': authors,
                'areas': raw_paper['Subject Areas'],
            }

            # Write row to CSV
            writer.writerow(paper)

            front_matter = [
                '-' * 3,
                'layout: paper',
                'title: "{}"'.format(paper['title']),
                'comments: true',
                'invisible: true',
                '-' * 3,
            ]
            data = [
                'Authors: {authors}'.format(authors=paper['authors']),
            ]
            formatted_data = ['<p class="text-left"><i>{}</i></p>'.format(d) for d in data]

            # Generate page
            outpath = os.path.join(args.outdir,  '{external_id}.md'.format(external_id=external_id))
            with open(outpath, 'w') as fout:
                page_data = [
                    '\n'.join(front_matter),
                    '\n'.join(formatted_data),
                    paper['abstract'],
                    '[<b><a href="https://storage.googleapis.com/rss2017-papers/{external_id}.pdf">Full Paper</a></b>]'.format(external_id=external_id),
                    '{% include disqus.html %}'
                ]
                fout.write('\n\n'.join(page_data))

            if args.submdir:
                camera_ready = os.path.join(args.submdir,
                    'Paper {internal_id}'.format(internal_id=internal_id))
                if not os.path.exists(camera_ready):
                    print('[FAIL] Missing directory {}'.format(camera_ready))
                    continue

                pdf_inpath = find_paper(camera_ready)
                if pdf_inpath is None:
                    print('[FAIL] Could not find paper in {}'.format(camera_ready))
                    continue

                pdf_outpath = os.path.join(args.submdir,
                                           '{external_id}.pdf'.format(external_id=external_id))
                shutil.copyfile(pdf_inpath, pdf_outpath)

def find_paper(camera_ready_dir, verbose=False):
    """
    Return the path to the actual camera-ready submission, ignoring author
    agreements.
    """
    def is_subm(fname):
        words = [
            'agree', 'copyright', 'waiver', 'form', 'release', 'letter',
            'New Doc 2017-05-30.pdf'.lower(),
            'loa.pdf',
            '[Untitled].pdf'.lower(),
            'final_05-29-2017-163350.pdf',
            'img-531072123-0001.pdf',
            '20160722101745_001.pdf',
        ]
        fname = fname.lower()
        return not any(w in fname for w in words)

    fnames = os.listdir(camera_ready_dir)

    if len(fnames) != 2 and verbose:
        print('[WARN] {} has {} files: {}'.format(camera_ready_dir, len(fnames), fnames))

    subms = [fname for fname in fnames if is_subm(fname)]

    if len(subms) == 1:
        pdf_inpath = [fname for fname in fnames if fname in subms][0]
        if verbose:
            agreement = [fname for fname in fnames if fname not in subms][0]
            print('[PASS] {}: Keeping "{}", ignoring "{}"'.format(
                camera_ready_dir, pdf_inpath, agreement))

        return os.path.join(camera_ready_dir, pdf_inpath)
    else:
        if verbose:
            print('[FAIL] {} has files {}'.format(camera_ready_dir, fnames))

        return None


if __name__ == '__main__':
    main()    
