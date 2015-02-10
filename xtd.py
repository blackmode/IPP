#!/usr/bin/env python3
#UTF-8
#XTD:xsluns01

import re
import os
import string
import xml.etree.ElementTree as xmlp
import argparse
import fileinput
import sys
from xml.dom import minidom


# napoveda
def Help ():
	napoveda = """\n\t======================== [ NAPOVEDA PROGRAMU ] ==================================
	|\t
	|\tVitejte v napovede skriptu XML to DDL do predmetu IPP
	|\tAutor: Tomas Slunsky, xsluns01@stud.fit.vutbr.cz
	|\t
	|\t[ PARAMETRY ]
	|\t--help  => slouzi k vypsani napovedy
	|\t--input=filename  => vstupni souboru,abs./relativni cesta
	|\t--output=filename => vystupni soubor,abs./relativni cesta
	|\t--header='hlavicka' => vypise hlavicku
	|\t--isvalid=filename => overeni, zdali lze obsah soubor vlozit do tabulek
	|\t--etc=n => kde n>=0, urcuje max.pocet sloupcu vzniklych ze stejnojmen. podelem.
	|\t -a => Nebudou se generovat sloupce z atributu
	|\t -b => pokud elem. obsahuje vice subelem. stejneho nazvu,tak uvazuje jen 1 s nejvys. dat.typem
	|\t -g => vypis ve formatu relaci mezi tabulkami
	|
	=================================================================================\n"""
	return napoveda


# zjisti typ polozky
def getType (inpt,atribut=False):
	inpt = str(inpt)
	if re.match (r"^(0|1|True|False)$",inpt) or inpt=="":
		return "BIT"
	elif re.match (r'^[0-9]+$',inpt):       #(?<![\w\.\+\-])[0-9]+(?![\w\.\+\-])
		return "INT"
		# vylepsit!
	elif re.match (r"^[0-9]*[\.]?[0-9felFEL]+$|^[0-9\.]*[eE][\+\-]?[0-9felFEL]+$|^0[xX][abcdefABCDEFpP0-9\.\+\-lL]*$|^[0-9]*[eE][0-9felFEL]$",inpt):
		return "FLOAT"
	elif re.match (r"[\w\W\s]*",inpt) and atribut==True:
		return "NVARCHAR"
	else:
		return "NTEXT"


# urceni velikosti datovych typu
def valOfType(dType):
	if   dType=="BIT"      		  : return 1
	elif dType=="INT"      		  : return 2
	elif dType=="FLOAT"   		  : return 3
	elif dType=="NVARCHAR" 		  : return 4
	elif dType=="NTEXT"   		  : return 5
	else						  : return 0


# err report
def error(msg,code):
	sys.stderr.write("ERROR: "+msg+"\n")
	exit(code)


# prida atributy elementu
def checkAttrib (atr,data,args,sufix):
	# pokud atrib existuje
	if atr.attrib and not args.a:
		# pro kazdy seznam vypisu tabulku a dalsi hodnoty
		for key in atr.attrib.keys():
			table=atr.tag
			value = atr.attrib[key]
			dic = atr.attrib
			dataType = getType(value,True) ## jedna se o atribut
			insert = key.lower()

			# pokud je tabulka jiz vlozena v datech, tak zkonroluje
			# zdali ten radek neni vicekrat potazmo aktualizuje jeho typ
			if table in data.keys():
				# pokud jiz sloupec existuje overim typ a prip.aktualizuju
				if insert in data[table].keys():
					if valOfType(data[table][insert]) < valOfType(dataType):
						data[table][insert] = dataType
				# jinak vkladam
				else:
					data[table][insert]=dataType
			# tabulka jeste neni vlozena, tak vlozim
			else:
				data[table]={insert:dataType}
	return data


#tisk XML to DDL
def XML2DDLprint (dictionary,args,xml_out_ver=1,mode=1):

	# automaticky rozpozna soubor ci stdout
	if not args.output:
		outFile = sys.stdout
	else:
		# pokus o otevreni
		try:
			outFile = open(args.output,"wt", encoding="utf-8")
		except:
			error("Chyba pri otevirani vystupniho souboru",3)

	# vlozeni hlavicky pro SQL a XML [pro XML volitelne]
	if args.header:
		if not args.g:
			outFile.write("--"+args.header+"\n\n")
		else:
			outFile.write("<!--"+args.header+"-->"+"\n\n")

	if not args.g:
		for table in dictionary.keys():

			# Prvni radek tabulky
			outFile.write("CREATE TABLE " + table + "(\n")

			# pocet sloupcu k vypsani a jejich nasledny vypis
			colls = len(dictionary[table])
			for val in dictionary[table].keys():

				# pokud zbyva vypsat vice jak jeden sloupec, tak bez carky na konci
				if colls>1:
				 	outFile.write("\t"+val+" "+dictionary[table][val]+",\n")
				 	colls=colls-1

				elif colls==1:
					outFile.write("\t"+val+" "+dictionary[table][val]+"\n")
					colls = 0

			outFile.write(");\n\n")
	else:
		# vlozeni na uvod
		outFile.write('<?xml version="1.0"?>\n')
		outFile.write('<tables>\n')

		# zpracovani tabulky
		for key in dictionary.keys():
			outFile.write('\t<table name=\"'+key+'\">\n')

			# zpracovani sloupcu tabulky
			for rel in dictionary[key]:

				# mod urcujici dat.stukturu
				if mode==1:
					tabulka = rel[0]
					vztah = rel[1]
				else:
					tabulka = rel
					vztah = dictionary[key][rel]

				if vztah=="eps":
					continue
					#vztah="N:M"
					pass

				# mod vypisu, tj poradi atributu 'to' a 'relation_type'
				if xml_out_ver==1:
					outFile.write('\t\t<relation to=\"'+tabulka+'\" relation_type=\"'+vztah+'\" />\n')
				else:
					outFile.write('\t\t<relation relation_type=\"'+vztah+'\" to=\"'+tabulka+'\" />\n')

			#ukonceni tabulky
			outFile.write('\t</table>\n')

		# ukonceni vypisu vech tabulek
		outFile.write('</tables>\n\n')

	# zavri soubor
	if args.output:
		outFile.close()

	return outFile


# keys into string
def countOfCols (columns):
	str_out = ""
	for key in columns:
		str_out = str_out+key+"\n"
	return str_out


# generovani DDL
def DDL_table (inpt,data,args):

	# sloupce
	prefix = "prk_"
	sufix  = "_id"
	pk     = "INT PRIMARY KEY"
	val    = "value"
	root = inpt.tag
	data_atrib={}
	#tmp_dict = {}

	# nacteni atributu a PK
	for atrpk in inpt.iter():

		# koren se preskoci
		if atrpk.tag==root: continue

		# pridam atributy do dat + do slovniku atributu pro kontrolu kolizi
		data = checkAttrib (atrpk,data,args,sufix)
		data_atrib = checkAttrib (atrpk,data_atrib,args,sufix)
		el = atrpk.tag.lower()

		#pokud je v datech, tak prida polozku
		#jinak vlozi tabulky a do ni tu polozku
		if el in data.keys():
			data[el][prefix+el+sufix]=pk
		else:
			data[el]={prefix+el+sufix:pk}

	# nacteni ostatnich sloupcu
	for elem in inpt.iter():

		# koren se preskoci
		if elem.tag.lower()==root: continue
		#print("PARENT:",elem.tag.lower())

		# pomocny slovnik pro stejne podelemnty elementu
		tmp_dict = {}

		# diva se na podelementy elemntu
		for sub_elem in elem.getchildren():
			#print("   |___CHILD:",sub_elem.tag.lower())

			# pokud je tabulka v datech
			if elem.tag.lower() in data.keys():

				# Overeni zdali nedochszi ke kolizi s atributy
				if elem.tag.lower() in data_atrib.keys():
					if (sub_elem.tag.lower()+sufix) in data_atrib[elem.tag.lower()].keys():
						error("Takovy element jiz je pouzit jako atribut, kolize [1]",90)

				# pokud pod-element neni jeste vlozen mezi sloupci elementu
				# tak jej vlozime, jeikoz je to klic do cizi tabulky tak INT
				if (sub_elem.tag.lower()+sufix) not in data[elem.tag.lower()].keys():
					if args.etc:
						if int(args.etc)==0:
							if data[sub_elem.tag.lower()]:
								if elem.tag.lower()+sufix not in data[sub_elem.tag.lower()].keys():
									data[sub_elem.tag.lower()][elem.tag.lower()+sufix]="INT"
						else:
							data[elem.tag.lower()][sub_elem.tag.lower()+sufix]="INT"
					else:
						data[elem.tag.lower()][sub_elem.tag.lower()+sufix]="INT"

				# jestlize hodnota mezi elementy nebyla vlozena jako sloupce do elmentu
				# a zaroven mezi elemnty je nejaky text, zjisti i jeho typ
				if val not in data[sub_elem.tag.lower()].keys() and data[sub_elem.tag.lower()]:
					if sub_elem.text and sub_elem.text.strip():
						  data[sub_elem.tag.lower()][val]=getType(str(sub_elem.text),False)

				# V opacnem pripade overime jestli value existuje a pokud ano upravime dat. typ
				elif val in data[sub_elem.tag.lower()].keys():
					if valOfType(data[sub_elem.tag.lower()][val]) < valOfType(getType(sub_elem.text,args.a)):
						data[sub_elem.tag.lower()][val] = getType(str(sub_elem.text),False)

				# Nahazi vsechny sloupce do retezce
				if sub_elem.tag.lower() not in tmp_dict:
					tmp_dict = {sub_elem.tag.lower():1}
				else:
					tmp_dict[sub_elem.tag.lower()] = tmp_dict[sub_elem.tag.lower()]+1

		#print(tmp_dict)
		# generuje sloupce pro etce=n kde n>=0 || n=inf
		for key in tmp_dict:
			# pokud je pocet vyskytu vetdsi jak 1 a neni zadan atc tj n=inf
			# postupne nagenerujeme sloupce pro stejne sub elem
			if (tmp_dict[key]>1):

				# takze je etc=n nebo etc>=sloupce
				if not args.etc or int(args.etc)>=tmp_dict[key]: 
					if not args.b:
						i=1
						while(i<(tmp_dict[key]+1)):

							# overeni jestli nedochazi je kolizi a pokud vlozime
							if elem.tag.lower() in data_atrib.keys():
								if key+str(i)+sufix in data_atrib[elem.tag.lower()].keys():
									error("Element: ["+key+str(i)+sufix+"] jiz je pouzit jako atribut, kolize [2]",90)

							# pokud sloupec jeste v tabulce neni tak vlozime
							if key+str(i)+sufix not in data[elem.tag.lower()].keys():
								data[elem.tag.lower()][key+str(i)+sufix]="INT"

							# pokud by existoval klic cizi tabulky bez cisla, tak ji smazeme
							if key+sufix in data[elem.tag.lower()].keys():
								del data[elem.tag.lower()][key+sufix]
								pass
							i+=1

				elif args.etc and tmp_dict[key]>int(args.etc):
					# smazeme pvodni sloupec
					if key+sufix in data[elem.tag.lower()].keys():
						del data[elem.tag.lower()][key+sufix]
						pass

					# overime zdali nove vkladany sloupec nekoliduje s atributy
					if sub_elem.tag.lower() in data_atrib.keys():
						if elem.tag.lower()+sufix in data_atrib[sub_elem.tag.lower()].keys():
							error("Element: ["+elem.tag.lower()+sufix+"] jiz je pouzit jako atribut, kolize [3]",90)

					# vlozime
					if elem.tag.lower()+sufix not in data[sub_elem.tag.lower()].keys():
						data[sub_elem.tag.lower()][elem.tag.lower()+sufix]="INT"
	

	return data


# overeni zdali jsou 2 tabulky v relaci
def checkRelations(data,a,b,mode=1):
	if mode==1:
		for col in data[a].keys():
			if re.match(r"^"+b.lower()+"[0-9]*_id$",col):
				#print(a,"-->",b)
				return True
		return False
	elif mode==2:
		if a in data.keys():
			for sub_table,relation in data[a]:
				if sub_table==b:
					return relation
		else:
			return False
	elif mode==3:
		for table, relation in relations:
			if table==a and relation ==b :
				return True
			else:
				return False


# algoritmus pro stanoveni relaci
def realations(data,args,mode=1):
	
	#how it works
	# seznam |  kam  | prikaz| rel.tab, relace napr 1:N |
	#relations[tabulka].append([tabulka, "typ relace"])

	#1.
	relations={}
	relations_dict={}


	#2.
	#(a): if a=b, pak R(a,b) = 1:1
	for a in data.keys():
		a=a.lower()
		for b in data.keys():
			b=b.lower()
			if a==b:
				relations[a] = [[b, "1:1"]]
				relations_dict[a]={b:"1:1"}

	#2
	for a in data.keys():
		a=a.lower()
		for b in data.keys():
			b=b.lower()
			#(b): if a!=b, a --> b & b --> a, R(a,b)=N:M
			if checkRelations(data,a,b)==True and checkRelations(data,b,a)==True:
				relations[a].append([b, "N:M"])
				relations_dict[a][b]="N:M"
				#print("Vztah je M:N",a,b)

			#(c): if a!=b, a --> b AND NOT b --> a, R(a,b)=N:1
			elif checkRelations(data,a,b)==True and checkRelations(data,b,a)==False:
				relations[a].append([b, "N:1"])
				relations_dict[a][b]="N:1"
				#print("Vztah je N:1",a,b)

			#(d): if a!=b, b --> a AND NOT a --> b, R(a,b)=1:N
			elif checkRelations(data,b,a)==True and checkRelations(data,a,b)==False:
				relations[a].append([b, "1:N"])
				relations_dict[a][b]="1:N"
				#print("Vztah je 1:N",a,b)

			#(e): else R(a,b)=eps
			else:
				if a!=b:
					relations[a].append([b, "eps"])
					relations_dict[a][b]="eps"


	#3
	for tab in relations.keys():
		for table in relations.keys():
			for sub_table in relations.keys():
				if checkRelations(relations,table,sub_table,2)=="eps":
					for sub_tab in relations.keys():
					
						if checkRelations(relations,table,sub_tab,2)=="1:N" and checkRelations(relations,sub_tab,sub_table,2)=="1:N":
							#print("A:B",table,sub_table,"A:C",checkRelations(relations,table,sub_tab,2),": 1:N","_______","C:B",checkRelations(relations,sub_tab,sub_table,2),": 1:N")
							relations_dict[table][sub_table]= "1:N"

							# clean
							if [sub_table, "eps"] in relations[table]:
								relations[table].remove([sub_table, "eps"])

							if [sub_table, "1:N"] not in relations[table]:
								relations[table].append([sub_table, "1:N"])

	#4
	for tab in relations.keys():
		for table in relations.keys():
			for sub_table in relations.keys():
				if checkRelations(relations,table,sub_table,2)=="eps":
					for sub_tab in relations.keys():

						if checkRelations(relations,table,sub_tab,2)=="N:1" and checkRelations(relations,sub_tab,sub_table,2)=="N:1":
							relations_dict[table][sub_table]= "N:1"

							# clean
							if [sub_table, "eps"] in relations[table]:
								relations[table].remove([sub_table, "eps"])

							if [sub_table, "N:1"] not in relations[table]:
								relations[table].append([sub_table, "N:1"])

	#5
	for table in relations.keys():
		for sub_table in relations.keys():
				for sub_tab in relations.keys():
					#print("A:",table,"B:",sub_table,"C:",sub_tab,checkRelations(relations,table,sub_tab,2),checkRelations(relations,sub_tab,sub_table,2))
					if checkRelations(relations,table,sub_tab,2)!="eps" and checkRelations(relations,sub_tab,sub_table,2)!="eps":

						#  ulozeni do promennych aby to nebylo tak dlouhy
						chck1 = relations_dict[table][sub_table]
						chck2 = relations_dict[sub_table][table]

						# overeni zdali jiz vazba existuje, jelikoz ma prednost
						if chck1=="eps" and chck2=="eps":
							relations_dict[table][sub_table]= "N:M"
							relations_dict[sub_table][table]= "N:M"

							# clean
							if [sub_table, "eps"] in relations[table]:
								relations[table].remove([sub_table, "eps"])

							if [table, "eps"] in relations[sub_table]:
								relations[sub_table].remove([table, "eps"])

							if [sub_table, "N:M"] not in relations[table]:
								relations[table].append([sub_table, "N:M"])

							if [table, "N:M"] not in relations[sub_table]:
								relations[sub_table].append([table, "N:M"])	
									
							
	if mode==1:
		return relations
	else:
		return relations_dict


#rozsireni isvalid
def isvalid(data,args):

	# rozsireni isvalid
	if args.isvalid:
		try:
			# nacitani vstupu zde, protoze senebude ubec zasahovat do osetreni vstupu
			# budeme se chovat jako kdyby to byl modul kterej si jen nacteme
			tree = xmlp.parse(os.path.abspath(os.path.basename(args.isvalid)))
			root = tree.getroot()
		except:
			error("Neplatny vstup --isvalid",2)

		isvalid_data_atrib={}
		isvalid_data = {}
		isvld_root = root.tag

		prefix = "prk_"
		sufix  = "_id"
		pk     = "INT PRIMARY KEY"
		val    = "value"

		# nacteni atributu a PK
		for isvld_atr in root.iter():

			# koren se preskoci
			if isvld_atr.tag==isvld_root: continue

			# pridam atributy 
			isvalid_data_atrib = checkAttrib (isvld_atr,isvalid_data_atrib,args,sufix)

	# pravidla:
	  # 1.) kolize: vsechny sloupce co maji stejny nazev jako atribut elementu
	  # 2.) pokud se sloupce shoduji a sloupec v tabulce ma mensi datovy typ jako ten co chceme vlozit, tak chyba, nejde to

	## add 1.)
	for par_elem in isvalid_data_atrib.keys():
		for ch_elem in isvalid_data_atrib[par_elem].keys():
			if par_elem in data.keys():
				if ch_elem in data[par_elem].keys():
					error("Doslo ke kolizi s atributem: ["+ch_elem+"]",91)

	# zpracovani XML
	isvalid_data = DDL_table(root,isvalid_data,args)

	# add 2.)
	for table in isvalid_data.keys():
		# pokud tabulka existuje v datech
		if table in data.keys():
			# nacteme sloupce tabulky isvalid
			for coll in isvalid_data[table].keys():
				# pokud se sloupec shoduje se sloupcem v datech
				if coll in data[table].keys():
					#print(table,coll, isvalid_data[table][coll],data[table][coll])

					if valOfType(isvalid_data[table][coll]) > valOfType(data[table][coll]):
						error("Nelze vlozit vetsi datovy: ["+isvalid_data[table][coll]+"] do ["+data[table][coll]+"]",91)

	# navrat aktualizovane tabulky
	for updt_key in isvalid_data.keys():
		if updt_key not in data.keys():
			data[updt_key]={prefix+updt_key+sufix:pk}
		
		for updt_col in isvalid_data[updt_key].keys():
			if updt_col not in data[updt_key].keys():
				data[updt_key][updt_col]=isvalid_data[updt_key][updt_col]
	return data


# zpracovani parametru
arguments = argparse.ArgumentParser(description="Skript do Predmetu IPP, XML to DDL")
arguments = argparse.ArgumentParser(add_help=False)
arguments.add_argument('-a', action="store_true", dest="a")
arguments.add_argument('-b', action="store_true", dest="b")
arguments.add_argument('-g', action="store_true", dest="g")
arguments.add_argument('--input',  action="store", dest="input")
arguments.add_argument('--output', action="store", dest="output")
arguments.add_argument('--header', action="store", dest="header")
arguments.add_argument('--etc',    action="store", dest="etc")
arguments.add_argument("--isvalid",action="store", dest="isvalid")
arguments.add_argument("--help", "-h", action="store_true", dest="help")


try:
	## naparsovani argumentu
	args = arguments.parse_args()
except:
	error("nepovoleny argument",1)

# overeni nekoretniho poctu ---> NEVIM , nutno zjistit
#if len(sys.argv)<2:
	#error("Neplatny pocet argumentu",1)

# overeni neplatnych kombinaci s help
if args.help:
	if len(sys.argv)!=2:
		error("Parametr help nesmi byt kombinovan",1)
	else:
		print(Help())
		exit(0)

# Overeni neplatnych kombinaci parametru
if (args.b and args.etc):
	error("Neplatna kombinace parametru: -b a --etc=n",1)

# overeni vstupu
if not args.input:
	inpt = sys.stdin # vstup bude standardni vstup
else:
	# vstup bude soubor
	inpt = args.input

	# test existence souboru
	if os.path.isfile(inpt)==False:
		# pokud soubor neexistoval, je mozne ze byla cesta zadana jinym formatem
		# proto zkusime cestu upravit na obecny tvar a pokus opakujeme
		inpt = os.path.abspath(os.path.basename(args.input))

	# posledni pokus o overeni existence
	if os.path.isfile(inpt)==False:
		error("Zadany vstupni soubor neexistuje",2)

	# test citelnosti 
	if os.access(inpt,os.R_OK)==False:
		error("Zadany vstupni soubor neni citelny",2)
try:
	tree = xmlp.parse(inpt)
	root = tree.getroot()
	datas={}
except:
	error("Neplatny vstup, xml.parse",2)

# overeni argumentu etc>=0 && etc==int
if args.etc and not re.match(r"^[\+]?[0-9]*$",str(args.etc)):
	error("Argument --etc musi obsahovat cele, nezaporne cislo, nikoli: "+args.etc,1)

#osetreni argumentu isvalid
if args.isvalid:
	# vstup isvalid
	isvld = os.path.abspath(os.path.basename(args.isvalid))

	#overeni existence
	if os.path.isfile(isvld)==False:
		error("Zadany vstupni soubor v argumentu --isvalid neexistuje",2)

	# test citelnosti 
	if os.access(isvld,os.R_OK)==False:
		error("Zadany vstupni soubor neni citelny",2)


# pocet parametru
for parametr in ["-a","-b","-g","--etc","--input","--output","--help","--isvalid","--header"]:
	if len(re.findall(r""+parametr+"", countOfCols (sys.argv)))>1:
		error("Nelze zadat jeden parametr vicekrat",1)


#1 --> to="book" relation_type="1:N"
#2 --> relation_type="1:N" to="book"
xml_ver=2

#1 --> slovnik + seznam
#2 --> slovnik + slovnik
mode=2

# vrati zpracovane tabulky
DDL = DDL_table(root,datas,args)

# zpracovani do funkce vcetne rozsieni
if args.isvalid: # isvalid(data,args)
	if not args.g:
		#isvalid(DDL,args)
		XML2DDLprint(isvalid(DDL,args),args)
	else:
		#realations(isvalid(DDL,args),args,mode)
		XML2DDLprint(realations(isvalid(DDL,args),args,mode),args,xml_ver,mode)
else:
	if not args.g:
		XML2DDLprint(DDL,args)
	else:
		#realations(DDL_table(root,datas,args),args,mode)
		XML2DDLprint(realations(DDL,args,mode),args,xml_ver,mode)

# success
exit(0)
