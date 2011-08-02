# [Back to docs.py](docs.html)

import epb.blast as Blast
from epb.data import DataSet
import os
import re
import sqlite3
import yaml

class Domain:
	def __init__(self, row):
		self.id = row[0]
		self.accession = row[1]
		self.domain_name = row[2]
		self.domain_accession = row[3]
		self.evalue = row[4]
		self.qstart = row[5]
		self.qend = row[6]
		self.dlength = row[7]
		self.dstart = row[8]
		self.dend = row[9]

class OrganismDatabase:
	class Guard:
		def in_order(self, f1, f2):
			f1(); f2()
	
	file_ext = ".db"
	
	def __init__(self, dbdir, slug):
		self.path = os.path.join(dbdir, slug) + self.file_ext
	
	def cursor(self):
		conn = sqlite3.connect(self.path)
		c = conn.cursor()
		guard = OrganismDatabase.Guard()
		guard.__enter__ = lambda: c
		guard.__exit__ = lambda *args: guard.in_order(c.close, conn.close)
		return guard
	
	def get_sequence(self, alignment):
		with self.cursor() as c:
			statement = c.execute('select sequences.sequence from sequences where sequences.fullname = ? limit 1', (alignment,))
			row = statement.fetchone()
			return row[0]

	def get_domains(self, alignment):
		with self.cursor() as c:
			statement = c.execute('select domains.* from domains where domains.accession = ?', (alignment,))
			return list(map(Domain, statement.fetchall()))

# === Organism ===
class Organism:
	def __init__(self, slug, info, **kwargs):
		self.slug = slug
		self.info = info
		
		self.blastdir = kwargs['blastdir']
		
		self.name = info.get('name', slug)
		self.database = OrganismDatabase(kwargs['dbdir'], slug)
		
	def blast(self, sequence):
		xml = Blast.get_xml(os.path.join(self.blastdir, self.slug), sequence)
		
		for datum in Blast.parse_xml(xml):
			datum['organism'] = self
			yield datum
		
	def url_for_gene(self, gene):
		match = re.match(self.info.get('fasta_header_format', ''), gene)
		if match:
			keys = match.groupdict()
			for k in keys: keys[k] = (keys[k] or '').strip()
		else:
			keys = {}
		return self.info.get('gene_url','#').format(**keys)
	
	def get_sequence(self, alignment):
		return self.database.get_sequence(alignment)
		
	def get_domains(self, alignment):
		return self.database.get_domains(alignment)

# === OrganismCollection ===
class OrganismCollection:
	ext = ".yaml"
	
	blastdir = None
	dbdir = None
	infodir = None

	def __init__(self, organisms):
		self.organisms = organisms
		
	def __len__(self):
		return len(self.organisms)

	# === blast ===
	def blast(self, sequence, **opts):		
		callback = opts.get("callback", None)
		
		data = []
		for organism in self.organisms:
			if callback: callback(organism)
			for datum in organism.blast(sequence):
				data.append(datum)
		
		return DataSet(data)

	# === find_all_by_categories ===
	@classmethod
	def find_all_by_categories(klass, categories):
		categories = [c.lower() for c in categories]

		info_files = [f for f in os.listdir(klass.infodir) if f.endswith(klass.ext)]

		organisms = []

		for fname in info_files:
			with open(os.path.join(klass.infodir, fname)) as f:
				info = yaml.load(f) or {}
				if True: #any((c.strip().lower() in categories) for c in info_categories):
					slug = fname[:-len(klass.ext)]
					o = Organism(slug, info,
					    blastdir = klass.blastdir,
					    dbdir = klass.dbdir,
					)
					organisms.append(o)

		return OrganismCollection(organisms)
