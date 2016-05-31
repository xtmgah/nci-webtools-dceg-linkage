#!/usr/bin/env python

# Create LDproxy function
def calculate_assoc(file,snp,pop,request,parameters):
	import csv,json,operator,os,sqlite3,subprocess,sys,time
	from multiprocessing.dummy import Pool
	start_time=time.time()

	# Set data directories
	data_dir="/local/content/ldlink/data/"
	gene_dir=data_dir+"refGene/sorted_refGene.txt.gz"
	recomb_dir=data_dir+"recomb/genetic_map_autosomes_combined_b37.txt.gz"
	snp_dir=data_dir+"snp142/snp142_annot_2.db"
	pop_dir=data_dir+"1000G/Phase3/samples/"
	vcf_dir=data_dir+"1000G/Phase3/genotypes/ALL.chr"
	tmp_dir="./tmp/"
	
	
	# Ensure tmp directory exists
	if not os.path.exists(tmp_dir):
		os.makedirs(tmp_dir)


	# Create JSON output
	out_json=open(tmp_dir+'proxy'+request+".json","w")
	output={}


	# Find coordinates (GRCh37/hg19) for SNP RS number
	# Connect to snp142 database
	conn=sqlite3.connect(snp_dir)
	conn.text_factory=str
	cur=conn.cursor()
	
	def get_coords(rs):
		id=rs.strip("rs")
		t=(id,)
		cur.execute("SELECT * FROM tbl_"+id[-1]+" WHERE id=?", t)
		return cur.fetchone()

	# Find RS number in snp142 database
	snp_coord=get_coords(snp)
	
	# Close snp142 connection
	cur.close()
	conn.close()
	
	if snp_coord==None:
		output["error"]=snp+" is not in dbSNP build 142."
		json_output=json.dumps(output, sort_keys=True, indent=2)
		print >> out_json, json_output
		out_json.close()
		return("","")
		raise
	
	
	# Open Association Data
	header_list=[]
	header_list.append(parameters["CHR"])
	header_list.append(parameters["POS"])
	header_list.append(parameters["P"])
	
	# Load input file
	assoc_data=open(file).readlines()
	header=assoc_data[0].strip().split()
	
	# Check header
	for item in header_list:
		if item not in header:
			output["error"]=key+" is not in the association file header."
			json_output=json.dumps(output, sort_keys=True, indent=2)
			print >> out_json, json_output
			out_json.close()
			return("","")
			raise		
	
	chr_index=header.index(parameters["CHR"])
	pos_index=header.index(parameters["POS"])
	p_index=header.index(parameters["P"])
	
	# Define window of interest around query SNP
	window=parameters["WINDOW"]
	delta=window/2
	coord1=int(snp_coord[2])-delta
	if coord1<0:
		coord1=0
	coord2=int(snp_coord[2])+delta
	
	# Generate Coordinate list
	assoc_coords=[]
	assoc_dict={}
	for i in range(1,len(assoc_data)):
		col=assoc_data[i].strip().split()
		if int(col[chr_index])==int(snp_coord[1]) and coord1<=int(col[pos_index])<=coord2:
			try:
				float(col[p_index])
			except ValueError:
				continue
			else:
				coord_i=col[chr_index]+":"+col[pos_index]+"-"+col[pos_index]
				assoc_coords.append(coord_i)
				assoc_dict[coord_i]=[col[p_index]]
			
	# Coordinate list checks
	if len(assoc_coords)==0:
		output["error"]="There are no variants in the association file with genomic coordinates inside the plotting window."
		json_output=json.dumps(output, sort_keys=True, indent=2)
		print >> out_json, json_output
		out_json.close()
		return("","")
		raise
	
	if snp_coord[1]+":"+snp_coord[2]+"-"+snp_coord[2] not in assoc_coords:
		output["error"]="Association file is missing a p-value for index variant "+snp+"."
		json_output=json.dumps(output, sort_keys=True, indent=2)
		print >> out_json, json_output
		out_json.close()
		return("","")
		raise
	
	
	
	# Select desired ancestral populations
	pops=pop.split("+")
	pop_dirs=[]
	for pop_i in pops:
		if pop_i in ["ALL","AFR","AMR","EAS","EUR","SAS","ACB","ASW","BEB","CDX","CEU","CHB","CHS","CLM","ESN","FIN","GBR","GIH","GWD","IBS","ITU","JPT","KHV","LWK","MSL","MXL","PEL","PJL","PUR","STU","TSI","YRI"]:
			pop_dirs.append(pop_dir+pop_i+".txt")
		else:
			output["error"]=pop_i+" is not an ancestral population. Choose one of the following ancestral populations: AFR, AMR, EAS, EUR, or SAS; or one of the following sub-populations: ACB, ASW, BEB, CDX, CEU, CHB, CHS, CLM, ESN, FIN, GBR, GIH, GWD, IBS, ITU, JPT, KHV, LWK, MSL, MXL, PEL, PJL, PUR, STU, TSI, or YRI."
			json_output=json.dumps(output, sort_keys=True, indent=2)
			print >> out_json, json_output
			out_json.close()
			return("","")
			raise

	get_pops="cat "+" ".join(pop_dirs)+" > "+tmp_dir+"pops_"+request+".txt"
	subprocess.call(get_pops, shell=True)


	# Get population ids
	pop_list=open(tmp_dir+"pops_"+request+".txt").readlines()
	ids=[]
	for i in range(len(pop_list)):
		ids.append(pop_list[i].strip())

	pop_ids=list(set(ids))


	# Extract query SNP phased genotypes
	vcf_file=vcf_dir+snp_coord[1]+".phase3_shapeit2_mvncall_integrated_v5.20130502.genotypes.vcf.gz"
	
	tabix_snp_h="tabix -H {0} | grep CHROM".format(vcf_file)
	proc_h=subprocess.Popen(tabix_snp_h, shell=True, stdout=subprocess.PIPE)
	head=proc_h.stdout.readlines()[0].strip().split()
	
	tabix_snp="tabix {0} {1}:{2}-{2} | grep -v -e END > {3}".format(vcf_file, snp_coord[1], snp_coord[2], tmp_dir+"snp_no_dups_"+request+".vcf")
	subprocess.call(tabix_snp, shell=True)


	# Check SNP is in the 1000G population, has the correct RS number, and not monoallelic 
	vcf=open(tmp_dir+"snp_no_dups_"+request+".vcf").readlines()
	
	if len(vcf)==0:
		output["error"]=snp+" is not in 1000G reference panel."
		json_output=json.dumps(output, sort_keys=True, indent=2)
		print >> out_json, json_output
		out_json.close()
		subprocess.call("rm "+tmp_dir+"pops_"+request+".txt", shell=True)
		subprocess.call("rm "+tmp_dir+"*"+request+"*.vcf", shell=True)
		return("","")
		raise
	elif len(vcf)>1:
		geno=[]
		for i in range(len(vcf)):
			if vcf[i].strip().split()[2]==snp:
				geno=vcf[i].strip().split()
		if geno==[]:
			output["error"]=snp+" is not in 1000G reference panel."
			json_output=json.dumps(output, sort_keys=True, indent=2)
			print >> out_json, json_output
			out_json.close()
			subprocess.call("rm "+tmp_dir+"pops_"+request+".txt", shell=True)
			subprocess.call("rm "+tmp_dir+"*"+request+"*.vcf", shell=True)
			return("","")
			raise
	else:
		geno=vcf[0].strip().split()
	
	if geno[2]!=snp:
		output["warning"]="Genomic position for query variant ("+snp+") does not match RS number at 1000G position ("+geno[2]+")"
		snp=geno[2]
		
	if "," in geno[3] or "," in geno[4]:
		output["error"]=snp+" is not a biallelic variant."
		json_output=json.dumps(output, sort_keys=True, indent=2)
		print >> out_json, json_output
		out_json.close()
		subprocess.call("rm "+tmp_dir+"pops_"+request+".txt", shell=True)
		subprocess.call("rm "+tmp_dir+"*"+request+"*.vcf", shell=True)
		return("","")
		raise
	
	
	index=[]
	for i in range(9,len(head)):
		if head[i] in pop_ids:
			index.append(i)

	genotypes={"0":0, "1":0}
	for i in index:
		sub_geno=geno[i].split("|")
		for j in sub_geno:
			if j in genotypes:
				genotypes[j]+=1
			else:
				genotypes[j]=1

	if genotypes["0"]==0 or genotypes["1"]==0:
		output["error"]=snp+" is monoallelic in the "+pop+" population."
		json_output=json.dumps(output, sort_keys=True, indent=2)
		print >> out_json, json_output
		out_json.close()
		subprocess.call("rm "+tmp_dir+"pops_"+request+".txt", shell=True)
		subprocess.call("rm "+tmp_dir+"*"+request+"*.vcf", shell=True)
		return("","")
		raise
	
	
	
	# Calculate proxy LD statistics in parallel
	print ""
	threads=4
	block=len(assoc_coords)/threads
	commands=[]
	for i in range(threads):
		if i==min(range(threads)) and i==max(range(threads)):
			command="python LDassoc_sub.py "+snp+" "+snp_coord[1]+" "+"_".join(assoc_coords)+" "+request+" "+str(i)
		elif i==min(range(threads)):
			command="python LDassoc_sub.py "+snp+" "+snp_coord[1]+" "+"_".join(assoc_coords[:block])+" "+request+" "+str(i)
		elif i==max(range(threads)):
			command="python LDassoc_sub.py "+snp+" "+snp_coord[1]+" "+"_".join(assoc_coords[(block*i)+1:])+" "+request+" "+str(i)
		else:
			command="python LDassoc_sub.py "+snp+" "+snp_coord[1]+" "+"_".join(assoc_coords[(block*i)+1:block*(i+1)])+" "+request+" "+str(i)
		commands.append(command)

	processes=[subprocess.Popen(command, shell=True, stdout=subprocess.PIPE) for command in commands]
	
	# collect output in parallel
	def get_output(process):
		return process.communicate()[0].splitlines()

	pool = Pool(len(processes))
	out_raw=pool.map(get_output, processes)
	pool.close()
	pool.join()
	
	
	# Aggregate output
	out_prox=[]
	for i in range(len(out_raw)):
		for j in range(len(out_raw[i])):
			col=out_raw[i][j].strip().split("\t")
			col[6]=int(col[6])
			col[7]=float(col[7])
			col[8]=float(col[8])
			col.append(abs(int(col[6])))
			pos_i_j=col[5].split(":")[1]
			coord_i_j=snp_coord[1]+":"+pos_i_j+"-"+pos_i_j
			if coord_i_j in assoc_dict:
				col.append(float(assoc_dict[coord_i_j][0]))
				out_prox.append(col)
	
	
	out_dist_sort=sorted(out_prox, key=operator.itemgetter(14))
	out_p_sort=sorted(out_dist_sort, key=operator.itemgetter(15), reverse=True)
	####################################
	# No longer sorting by R2 or D'!!! #
	# Need to decide on UCSC output style #
	####################################
	
	
	# Populate JSON and text output
	outfile=open(tmp_dir+"proxy"+request+".txt","w")
	header=["RS_Number","Coord","Alleles","MAF","Distance","Dprime","R2","Correlated_Alleles","RegulomeDB","Function"]
	print >> outfile, "\t".join(header)
	
	track=open(tmp_dir+"track"+request+".txt","w")
	print >> track, "browser position chr"+str(snp_coord[1])+":"+str(coord1)+"-"+str(coord2)
	print >> track, ""
	print >> track, "track name=\""+snp+"\" description=\"Query Variant: "+snp+"\" color=108,108,255"
	
	query_snp={}
	query_snp["RS"]=out_p_sort[0][3]
	query_snp["Alleles"]=out_p_sort[0][1]
	query_snp["Coord"]=out_p_sort[0][2]
	query_snp["Dist"]=out_p_sort[0][6]
	query_snp["Dprime"]=str(round(float(out_p_sort[0][7]),4))
	query_snp["R2"]=str(round(float(out_p_sort[0][8]),4))
	query_snp["Corr_Alleles"]=out_p_sort[0][9]
	query_snp["RegulomeDB"]=out_p_sort[0][10]
	query_snp["MAF"]=str(round(float(out_p_sort[0][11]),4))
	query_snp["Function"]=out_p_sort[0][13]
	query_snp["P-value"]=out_p_sort[0][15]

	output["query_snp"]=query_snp
	
	temp=[query_snp["RS"],query_snp["Coord"],query_snp["Alleles"],query_snp["MAF"],str(query_snp["Dist"]),str(query_snp["Dprime"]),str(query_snp["R2"]),query_snp["Corr_Alleles"],query_snp["RegulomeDB"],query_snp["Function"]]
	print >> outfile, "\t".join(temp)
	
	chr,pos=query_snp["Coord"].split(':')
	temp2=[chr,pos,pos,query_snp["RS"]]
	print >> track, "\t".join(temp2)
	print >> track, ""
	print >> track, "track name=\"0.8<R2<1.0\" description=\"Proxy Variants with 0.8<R2<1.0\" color=198,129,0"
	
	
	proxies={}
	rows=[]
	digits=len(str(len(out_p_sort)))
	r2_d_prior=1
	counter=0
	cutoff=[0.8,0.6,0.4,0.2,0.0]
	
	for i in range(1,len(out_p_sort)):
		if float(out_p_sort[i][8])>0.01 and out_p_sort[i][3]!=snp:
			proxy_info={}
			row=[]
			proxy_info["RS"]=out_p_sort[i][3]
			proxy_info["Alleles"]=out_p_sort[i][4]
			proxy_info["Coord"]=out_p_sort[i][5]
			proxy_info["Dist"]=out_p_sort[i][6]
			proxy_info["Dprime"]=str(round(float(out_p_sort[i][7]),4))
			proxy_info["R2"]=str(round(float(out_p_sort[i][8]),4))
			proxy_info["Corr_Alleles"]=out_p_sort[i][9]
			proxy_info["RegulomeDB"]=out_p_sort[i][10]
			proxy_info["MAF"]=str(round(float(out_p_sort[i][12]),4))
			proxy_info["Function"]=out_p_sort[i][13]
			proxy_info["P-value"]=out_p_sort[i][15]
			proxies["proxy_"+(digits-len(str(i)))*"0"+str(i)]=proxy_info
			chr,pos=proxy_info["Coord"].split(':')
			
			# Adding a row for the Data Table
			row.append(proxy_info["RS"])
			row.append(chr)
			row.append(pos)
			row.append(proxy_info["Alleles"])
			row.append(str(round(float(proxy_info["MAF"]),4)))
			row.append(proxy_info["Dist"])
			row.append(str(round(float(proxy_info["Dprime"]),4)))
			row.append(str(round(float(proxy_info["R2"]),4)))
			row.append(proxy_info["Corr_Alleles"])
			row.append(proxy_info["RegulomeDB"])
			row.append("HaploReg link")
			row.append(proxy_info["Function"])
			row.append(proxy_info["P-value"])
			rows.append(row)
			
			temp=[proxy_info["RS"],proxy_info["Coord"],proxy_info["Alleles"],proxy_info["MAF"],str(proxy_info["Dist"]),str(proxy_info["Dprime"]),str(proxy_info["R2"]),proxy_info["Corr_Alleles"],proxy_info["RegulomeDB"],proxy_info["Function"]]
			print >> outfile, "\t".join(temp)
			
			temp2=[chr,pos,pos,proxy_info["RS"]]
			print >> track, "\t".join(temp2)
			
			if cutoff[counter]<r2_d_prior and float(proxy_info["R2"])<=cutoff[counter]:
				print >> track, ""
				print >> track, "track name=\""+str(cutoff[counter+1])+"<R2<"+str(cutoff[counter])+"\" description=\"Proxy Variants with "+str(cutoff[counter+1])+"<R2<"+str(cutoff[counter])+"\" color=198,129,0"
				counter+=1
			
			r2_d_prior=proxy_info["R2"]

	output["aaData"]=rows
	output["proxy_snps"]=proxies
	
	
	# Output JSON and text file
	json_output=json.dumps(output, sort_keys=True, indent=2)
	print >> out_json, json_output
	out_json.close()
	
	outfile.close()
	track.close()
	
	
	
	# Organize scatter plot data
	from math import log10
	q_rs=[]
	q_allele=[]
	q_coord=[]
	q_maf=[]
	p_rs=[]
	p_allele=[]
	p_coord=[]
	p_maf=[]
	dist=[]
	d_prime=[]
	d_prime_round=[]
	r2=[]
	r2_round=[]
	corr_alleles=[]
	regdb=[]
	funct=[]
	color=[]
	alpha=[]
	size=[]
	p_val=[]
	neg_log_p=[]
	for i in range(len(out_p_sort)):
		q_rs_i,q_allele_i,q_coord_i,p_rs_i,p_allele_i,p_coord_i,dist_i,d_prime_i,r2_i,corr_alleles_i,regdb_i,q_maf_i,p_maf_i,funct_i,dist_abs,p_val_i=out_p_sort[i]
		
		q_rs.append(q_rs_i)
		q_allele.append(q_allele_i)
		q_coord.append(float(q_coord_i.split(":")[1])/1000000)
		q_maf.append(str(round(float(q_maf_i),4)))
		if p_rs_i==".":
			p_rs_i=p_coord_i
		p_rs.append(p_rs_i)
		p_allele.append(p_allele_i)
		p_coord.append(float(p_coord_i.split(":")[1])/1000000)
		p_maf.append(str(round(float(p_maf_i),4)))
		dist.append(str(round(dist_i/1000000.0,4)))
		d_prime.append(float(d_prime_i))
		d_prime_round.append(str(round(float(d_prime_i),4)))
		r2.append(float(r2_i))
		r2_round.append(str(round(float(r2_i),4)))
		corr_alleles.append(corr_alleles_i)
		
		# P-value
		p_val.append(p_val_i)
		neg_log_p.append(-log10(p_val_i))
		
		# Correct Missing Annotations
		if regdb_i==".":
			regdb_i=""
		regdb.append(regdb_i)
		if funct_i==".":
			funct_i=""
		if funct_i=="NA":
			funct_i="none"
		funct.append(funct_i)
		
		# Set Color
		if p_rs_i==snp:
			color_i="blue"
			alpha_i=0.7
		else:
			color_i="red"
			alpha_i=1-(0.8-0.5*float(r2_i))
		color.append(color_i)
		alpha.append(alpha_i)
		
		# Set Size
		size_i=9+float(p_maf_i)*14.0
		size.append(size_i)
	
	# Begin Bokeh Plotting
	from collections import OrderedDict
	from bokeh.embed import components,file_html
	from bokeh.models import HoverTool,LinearAxis,Range1d
	from bokeh.plotting import ColumnDataSource,curdoc,figure,output_file,reset_output,save
	from bokeh.resources import CDN
	
	reset_output()
	
	source=ColumnDataSource(
		data=dict(
			qrs=q_rs,
			q_alle=q_allele,
			q_maf=q_maf,
			prs=p_rs,
			p_alle=p_allele,
			p_maf=p_maf,
			dist=dist,
			r=r2_round,
			d=d_prime_round,
			alleles=corr_alleles,
			regdb=regdb,
			funct=funct,
			p_val=p_val,
		)
	)
	
	
	# Proxy Plot
	x=p_coord
	y=neg_log_p
	
	whitespace=0.01
	xr=Range1d(start=coord1/1000000.0-whitespace, end=coord2/1000000.0+whitespace)
	yr=Range1d(start=-0.03, end=max(y)*1.03)
	sup_2=u"\u00B2"

	proxy_plot=figure(
				title="Proxies for "+snp+" in "+pop,
				min_border_top=2, min_border_bottom=2, min_border_left=60, min_border_right=60, h_symmetry=False, v_symmetry=False,
				plot_width=900,
				plot_height=600,
				x_range=xr, y_range=yr,
				tools="hover,tap,pan,box_zoom,box_select,reset,previewsave", logo=None,
				toolbar_location="above")
	
	# Add recombination rate
	tabix_recomb="tabix -fh {0} {1}:{2}-{3} > {4}".format(recomb_dir, snp_coord[1], coord1-whitespace, coord2+whitespace, tmp_dir+"recomb_"+request+".txt")
	subprocess.call(tabix_recomb, shell=True)
	filename=tmp_dir+"recomb_"+request+".txt"
	recomb_raw=open(filename).readlines()
	recomb_x=[]
	recomb_y=[]
	for i in range(len(recomb_raw)):
		chr,pos,rate=recomb_raw[i].strip().split()
		recomb_x.append(int(pos)/1000000.0)
		recomb_y.append(float(rate)/1.0)  ## Divided by 100 previously
	
	proxy_plot.line(recomb_x, recomb_y, size=12, color="black", alpha=0.5)
	
	# Add genome-wide significance
	a = [min(p_coord),max(p_coord)]
	b = [-log10(0.00000005),-log10(0.00000005)]
	proxy_plot.line(a, b, color="blue", alpha=0.5)
	
	proxy_plot.circle(x, y, size=size, source=source, color=color, alpha=alpha)
	
	hover=proxy_plot.select(dict(type=HoverTool))
	hover.tooltips=OrderedDict([
		("Variant", "@prs @p_alle"),
		("P-value", "@p_val"),
		("Distance (Mb)", "@dist"),
		("MAF", "@p_maf"),
		("R"+sup_2+" ("+q_rs[0]+")", "@r"),
		("D\' ("+q_rs[0]+")", "@d"),
		("Correlated Alleles", "@alleles"),
		("RegulomeDB", "@regdb"),
		("Functional Class", "@funct"),
	])
	
	proxy_plot.text(x, y, text=regdb, alpha=1, text_font_size="7pt",
					text_baseline="middle", text_align="center", angle=0)
	
	proxy_plot.yaxis.axis_label="-log10 P-value"
	
	proxy_plot.extra_y_ranges = {"y2_axis": Range1d(start=-3, end=103)}
	proxy_plot.add_layout(LinearAxis(y_range_name="y2_axis", axis_label="Combined Recombination Rate (cM/Mb)"), "right")  ## Need to confirm units
	
	
	# Rug Plot
	y2_ll=[-0.03]*len(x)
	y2_ul=[1.03]*len(x)
	yr_rug=Range1d(start=-0.03, end=1.03)
	
	rug=figure(
			x_range=xr, y_range=yr_rug, border_fill='white', y_axis_type=None,
			title="", min_border_top=2, min_border_bottom=2, min_border_left=60, min_border_right=60, h_symmetry=False, v_symmetry=False,
			plot_width=900, plot_height=50, tools="xpan,tap")

	rug.segment(x, y2_ll, x, y2_ul, source=source, color=color, alpha=alpha, line_width=1)
	rug.toolbar_location=None
	
	
	# Gene Plot
	tabix_gene="tabix -fh {0} {1}:{2}-{3} > {4}".format(gene_dir, snp_coord[1], coord1, coord2, tmp_dir+"genes_"+request+".txt")
	subprocess.call(tabix_gene, shell=True)
	filename=tmp_dir+"genes_"+request+".txt"
	genes_raw=open(filename).readlines()
	
	genes_plot_start=[]
	genes_plot_end=[]
	genes_plot_y=[]
	genes_plot_name=[]
	exons_plot_x=[]
	exons_plot_y=[]
	exons_plot_w=[]
	exons_plot_h=[]
	exons_plot_name=[]
	exons_plot_id=[]
	exons_plot_exon=[]
	lines=[0]
	gap=80000
	tall=0.75
	if genes_raw!=None:
		for i in range(len(genes_raw)):
			bin,name_id,chrom,strand,txStart,txEnd,cdsStart,cdsEnd,exonCount,exonStarts,exonEnds,score,name2,cdsStartStat,cdsEndStat,exonFrames=genes_raw[i].strip().split()
			name=name2
			id=name_id
			e_start=exonStarts.split(",")
			e_end=exonEnds.split(",")
			
			# Determine Y Coordinate
			i=0
			y_coord=None
			while y_coord==None:
				if i>len(lines)-1:
					y_coord=i+1
					lines.append(int(txEnd))
				elif int(txStart)>(gap+lines[i]):
					y_coord=i+1
					lines[i]=int(txEnd)
				else:
					i+=1
			
			genes_plot_start.append(int(txStart)/1000000.0)
			genes_plot_end.append(int(txEnd)/1000000.0)
			genes_plot_y.append(y_coord)
			genes_plot_name.append(name+"  ")
			
			for i in range(len(e_start)-1):
				if strand=="+":
					exon=i+1
				else:
					exon=len(e_start)-1-i
				
				width=(int(e_end[i])-int(e_start[i]))/1000000.0
				x_coord=int(e_start[i])/1000000.0+(width/2)
				
				exons_plot_x.append(x_coord)
				exons_plot_y.append(y_coord)
				exons_plot_w.append(width)
				exons_plot_h.append(tall)
				exons_plot_name.append(name)
				exons_plot_id.append(id)
				exons_plot_exon.append(exon)


	n_rows=len(lines)
	genes_plot_yn=[n_rows-x+0.5 for x in genes_plot_y]
	exons_plot_yn=[n_rows-x+0.5 for x in exons_plot_y]
	yr2=Range1d(start=0, end=n_rows)
	
	source2=ColumnDataSource(
		data=dict(
			exons_plot_name=exons_plot_name,
			exons_plot_id=exons_plot_id,
			exons_plot_exon=exons_plot_exon,
		)
	)
	
	if len(lines)<3:
	    plot_h_pix=150
	else:
	    plot_h_pix=150+(len(lines)-2)*50
		
	
	gene_plot=figure(
					x_range=xr, y_range=yr2, border_fill='white', 
					title="", min_border_top=2, min_border_bottom=2, min_border_left=60, min_border_right=60, h_symmetry=False, v_symmetry=False,
					plot_width=900, plot_height=plot_h_pix, tools="hover,tap,xpan,box_zoom,reset,previewsave", logo=None)
					
	gene_plot.segment(genes_plot_start, genes_plot_yn, genes_plot_end, genes_plot_yn, color="black", alpha=1, line_width=2)
	gene_plot.rect(exons_plot_x, exons_plot_yn, exons_plot_w, exons_plot_h, source=source2, fill_color="grey", line_color="grey")
	gene_plot.xaxis.axis_label="Chromosome "+snp_coord[1]+" Coordinate (Mb)(GRCh37)"
	gene_plot.yaxis.axis_label="Genes"
	gene_plot.ygrid.grid_line_color=None
	gene_plot.yaxis.axis_line_color=None
	gene_plot.yaxis.minor_tick_line_color=None
	gene_plot.yaxis.major_tick_line_color=None
	gene_plot.yaxis.major_label_text_color=None
	
	hover=gene_plot.select(dict(type=HoverTool))
	hover.tooltips=OrderedDict([
		("Gene", "@exons_plot_name"),
		("ID", "@exons_plot_id"),
		("Exon", "@exons_plot_exon"),
	])
	
	gene_plot.text(genes_plot_start, genes_plot_yn, text=genes_plot_name, alpha=1, text_font_size="7pt",
		 text_font_style="bold", text_baseline="middle", text_align="right", angle=0)
	

	gene_plot.toolbar_location="below"
	
	#############################
	# Comment out after testing #
	#############################
	html=file_html(curdoc(), CDN, "Test Plot")
	out_html=open("LDassoc.html","w")
	print >> out_html, html
	out_html.close()
	
	out_script,out_div=components(curdoc(), CDN)
	reset_output()
	
	
	
	
	
	
	
	# Print run time statistics
	pop_list=open(tmp_dir+"pops_"+request+".txt").readlines()
	print "\nNumber of Individuals: "+str(len(pop_list))

	print "SNPs in Region: "+str(len(out_prox))

	duration=time.time() - start_time
	print "Run time: "+str(duration)+" seconds\n"


	# Remove temporary files
	subprocess.call("rm "+tmp_dir+"pops_"+request+".txt", shell=True)
	subprocess.call("rm "+tmp_dir+"*"+request+"*.vcf", shell=True)
	subprocess.call("rm "+tmp_dir+"genes_"+request+".txt", shell=True)
	subprocess.call("rm "+tmp_dir+"recomb_"+request+".txt", shell=True)


	# Return plot output
	return(out_script,out_div)


def main():
	import json,sys
	tmp_dir="./tmp/"

	# Create header mapping
	parameters={}
	parameters["P"]="P"
	parameters["CHR"]="CHR"
	parameters["POS"]="BP"
	parameters["WINDOW"]=1500000
	
	# Import LDproxy options
	if len(sys.argv)==5:
		file=sys.argv[1]
		snp=sys.argv[2]
		pop=sys.argv[3]
		request=sys.argv[4]
		parameters=parameters
	elif len(sys.argv)==6:
		file=sys.argv[1]
		snp=sys.argv[2]
		pop=sys.argv[3]
		request=sys.argv[4]
		parameters=sys.argv[5]
	else:
		print "Correct useage is: LDassoc.py file snp populations request parameters"
		sys.exit()


	
	# Run function
	out_script,out_div=calculate_assoc(file,snp,pop,request,parameters)
	
	# Print script and div output
	#out_script_line=out_script.split("\n")
	#for i in range(len(out_script_line)):
		#print out_script_line[i]
	#print ""
	#
	#print out_div
	#print ""
	
	
	# Print output
	with open(tmp_dir+"proxy"+request+".json") as f:
		json_dict=json.load(f)

	try:
		json_dict["error"]

	except KeyError:
		head=["RS_Number","Coord","Alleles","MAF","Distance","Dprime","R2","Correlated_Alleles","RegulomeDB","Functional_Class"]
		print "\t".join(head)
		temp=[json_dict["query_snp"]["RS"],json_dict["query_snp"]["Coord"],json_dict["query_snp"]["Alleles"],json_dict["query_snp"]["MAF"],str(json_dict["query_snp"]["Dist"]),str(json_dict["query_snp"]["Dprime"]),str(json_dict["query_snp"]["R2"]),json_dict["query_snp"]["Corr_Alleles"],json_dict["query_snp"]["RegulomeDB"],json_dict["query_snp"]["Function"]]
		print "\t".join(temp)
		for k in sorted(json_dict["proxy_snps"].keys())[0:10]:
			temp=[json_dict["proxy_snps"][k]["RS"],json_dict["proxy_snps"][k]["Coord"],json_dict["proxy_snps"][k]["Alleles"],json_dict["proxy_snps"][k]["MAF"],str(json_dict["proxy_snps"][k]["Dist"]),str(json_dict["proxy_snps"][k]["Dprime"]),str(json_dict["proxy_snps"][k]["R2"]),json_dict["proxy_snps"][k]["Corr_Alleles"],json_dict["proxy_snps"][k]["RegulomeDB"],json_dict["proxy_snps"][k]["Function"]]
			print "\t".join(temp)
		print ""

	else:
		print ""
		print json_dict["error"]
		print ""
	
	try:
		json_dict["warning"]
	except KeyError:
		print ""
	else:
		print "WARNING: "+json_dict["warning"]+"!"
		print ""


if __name__ == "__main__":
	main()
