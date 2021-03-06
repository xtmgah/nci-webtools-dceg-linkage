import yaml
import json
import sys
import json, math, operator, os, sqlite3, subprocess

# LDmatrix subprocess to export bokeh to high quality images in the background

def calculate_matrix_svg(snplst, pop, request, r2_d="r2"):

    # Set data directories using config.yml
    with open('config.yml', 'r') as f:
        config = yaml.load(f)
    gene_dir=config['data']['gene_dir']
    snp_dir=config['data']['snp_dir']
    pop_dir=config['data']['pop_dir']
    vcf_dir=config['data']['vcf_dir']

    tmp_dir = "./tmp/"

    # Ensure tmp directory exists
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    # Open SNP list file
    snps_raw = open(snplst).readlines()

    # Remove duplicate RS numbers
    snps = []
    for snp_raw in snps_raw:
        snp = snp_raw.strip().split()
        if snp not in snps:
            snps.append(snp)

    # Select desired ancestral populations
    pops = pop.split("+")
    pop_dirs = []
    for pop_i in pops:
        if pop_i in ["ALL", "AFR", "AMR", "EAS", "EUR", "SAS", "ACB", "ASW", "BEB", "CDX", "CEU", "CHB", "CHS", "CLM", "ESN", "FIN", "GBR", "GIH", "GWD", "IBS", "ITU", "JPT", "KHV", "LWK", "MSL", "MXL", "PEL", "PJL", "PUR", "STU", "TSI", "YRI"]:
            pop_dirs.append(pop_dir + pop_i + ".txt")

    get_pops = "cat " + " ".join(pop_dirs)
    proc = subprocess.Popen(get_pops, shell=True, stdout=subprocess.PIPE)
    pop_list = proc.stdout.readlines()

    ids = [i.strip() for i in pop_list]
    pop_ids = list(set(ids))

    # Connect to snp database
    conn = sqlite3.connect(snp_dir)
    conn.text_factory = str
    cur = conn.cursor()

    def get_coords(rs):
        id = rs.strip("rs")
        t = (id,)
        cur.execute("SELECT * FROM tbl_" + id[-1] + " WHERE id=?", t)
        return cur.fetchone()

    # Find RS numbers in snp database
    rs_nums = []
    snp_pos = []
    snp_coords = []
    tabix_coords = ""
    for snp_i in snps:
        if len(snp_i) > 0:
            if len(snp_i[0]) > 2:
                if snp_i[0][0:2] == "rs" and snp_i[0][-1].isdigit():
                    snp_coord = get_coords(snp_i[0])
                    if snp_coord != None:
                        rs_nums.append(snp_i[0])
                        snp_pos.append(snp_coord[2])
                        temp = [snp_i[0], snp_coord[1], snp_coord[2]]
                        snp_coords.append(temp)

    # Close snp connection
    cur.close()
    conn.close()


    # Check max distance between SNPs
    distance_bp = []
    for i in range(len(snp_coords)):
        distance_bp.append(int(snp_coords[i][2]))

    # Sort coordinates and make tabix formatted coordinates
    snp_pos_int = [int(i) for i in snp_pos]
    snp_pos_int.sort()
    snp_coord_str = [snp_coords[0][1] + ":" +
                     str(i) + "-" + str(i) for i in snp_pos_int]
    tabix_coords = " " + " ".join(snp_coord_str)

    # Extract 1000 Genomes phased genotypes
    vcf_file = vcf_dir + \
        snp_coords[0][
            1] + ".phase3_shapeit2_mvncall_integrated_v5.20130502.genotypes.vcf.gz"
    tabix_snps = "tabix -h {0}{1} | grep -v -e END".format(
        vcf_file, tabix_coords)
    proc = subprocess.Popen(tabix_snps, shell=True, stdout=subprocess.PIPE)

    # Define function to correct indel alleles
    def set_alleles(a1, a2):
        if len(a1) == 1 and len(a2) == 1:
            a1_n = a1
            a2_n = a2
        elif len(a1) == 1 and len(a2) > 1:
            a1_n = "-"
            a2_n = a2[1:]
        elif len(a1) > 1 and len(a2) == 1:
            a1_n = a1[1:]
            a2_n = "-"
        elif len(a1) > 1 and len(a2) > 1:
            a1_n = a1[1:]
            a2_n = a2[1:]
        return(a1_n, a2_n)

    # Import SNP VCF files
    vcf = proc.stdout.readlines()

    h = 0
    while vcf[h][0:2] == "##":
        h += 1

    head = vcf[h].strip().split()

    # Extract haplotypes
    index = []
    for i in range(9, len(head)):
        if head[i] in pop_ids:
            index.append(i)

    hap1 = [[]]
    for i in range(len(index) - 1):
        hap1.append([])
    hap2 = [[]]
    for i in range(len(index) - 1):
        hap2.append([])

    rsnum_lst = []
    allele_lst = []
    pos_lst = []

    for g in range(h + 1, len(vcf)):
        geno = vcf[g].strip().split()
        if geno[1] not in snp_pos:
            continue

        if snp_pos.count(geno[1]) == 1:
            rs_query = rs_nums[snp_pos.index(geno[1])]

        else:
            pos_index = []
            for p in range(len(snp_pos)):
                if snp_pos[p] == geno[1]:
                    pos_index.append(p)
            for p in pos_index:
                if rs_nums[p] not in rsnum_lst:
                    rs_query = rs_nums[p]
                    break

        if rs_query in rsnum_lst:
            continue

        rs_1000g = geno[2]

        if rs_query == rs_1000g:
            rsnum = rs_1000g
        else:
            count = -2
            found = "false"
            while count <= 2 and count + g < len(vcf):
                geno_next = vcf[g + count].strip().split()
                if rs_query == geno_next[2]:
                    found = "true"
                    break
                count += 1

            if found == "false":
                indx = [i[0] for i in snps].index(rs_query)
                # snps[indx][0] = geno[2]
                # rsnum = geno[2]
                snps[indx][0]=rs_query
                rsnum=rs_query
            else:
                continue

        if "," not in geno[3] and "," not in geno[4]:
            a1, a2 = set_alleles(geno[3], geno[4])
            for i in range(len(index)):
                if geno[index[i]] == "0|0":
                    hap1[i].append(a1)
                    hap2[i].append(a1)
                elif geno[index[i]] == "0|1":
                    hap1[i].append(a1)
                    hap2[i].append(a2)
                elif geno[index[i]] == "1|0":
                    hap1[i].append(a2)
                    hap2[i].append(a1)
                elif geno[index[i]] == "1|1":
                    hap1[i].append(a2)
                    hap2[i].append(a2)
                elif geno[index[i]] == "0":
                    hap1[i].append(a1)
                    hap2[i].append(".")
                elif geno[index[i]] == "1":
                    hap1[i].append(a2)
                    hap2[i].append(".")
                else:
                    hap1[i].append(".")
                    hap2[i].append(".")

            rsnum_lst.append(rsnum)

            position = "chr" + geno[0] + ":" + geno[1] + "-" + geno[1]
            pos_lst.append(position)
            alleles = a1 + "/" + a2
            allele_lst.append(alleles)

    # Calculate Pairwise LD Statistics
    all_haps = hap1 + hap2
    ld_matrix = [[[None for v in range(2)] for i in range(
        len(all_haps[0]))] for j in range(len(all_haps[0]))]

    for i in range(len(all_haps[0])):
        for j in range(i, len(all_haps[0])):
            hap = {}
            for k in range(len(all_haps)):
                # Extract haplotypes
                hap_k = all_haps[k][i] + all_haps[k][j]
                if hap_k in hap:
                    hap[hap_k] += 1
                else:
                    hap[hap_k] = 1

            # Remove Missing Haplotypes
            keys = hap.keys()
            for key in keys:
                if "." in key:
                    hap.pop(key, None)

            # Check all haplotypes are present
            if len(hap) != 4:
                snp_i_a = allele_lst[i].split("/")
                snp_j_a = allele_lst[j].split("/")
                haps = [snp_i_a[0] + snp_j_a[0], snp_i_a[0] + snp_j_a[1],
                        snp_i_a[1] + snp_j_a[0], snp_i_a[1] + snp_j_a[1]]
                for h in haps:
                    if h not in hap:
                        hap[h] = 0

            # Perform LD calculations
            A = hap[sorted(hap)[0]]
            B = hap[sorted(hap)[1]]
            C = hap[sorted(hap)[2]]
            D = hap[sorted(hap)[3]]
            tmax = max(A, B, C, D)
            delta = float(A * D - B * C)
            Ms = float((A + C) * (B + D) * (A + B) * (C + D))
            if Ms != 0:
                # D prime
                if delta < 0:
                    D_prime = round(
                        abs(delta / min((A + C) * (A + B), (B + D) * (C + D))), 3)
                else:
                    D_prime = round(
                        abs(delta / min((A + C) * (C + D), (A + B) * (B + D))), 3)

                # R2
                r2 = round((delta**2) / Ms, 3)

                # Find Correlated Alleles
                if r2 > 0.1:
                    N = A + B + C + D
                    # Expected Cell Counts
                    eA = (A + B) * (A + C) / N
                    eB = (B + A) * (B + D) / N
                    eC = (C + A) * (C + D) / N
                    eD = (D + C) * (D + B) / N

                    # Calculate Deltas
                    dA = (A - eA)**2
                    dB = (B - eB)**2
                    dC = (C - eC)**2
                    dD = (D - eD)**2
                    dmax = max(dA, dB, dC, dD)

                    if dA == dB == dC == dD:
                        if tmax == dA or tmax == dD:
                            match = sorted(hap)[0][
                                0] + "=" + sorted(hap)[0][1] + "," + sorted(hap)[2][0] + "=" + sorted(hap)[1][1]
                        else:
                            match = sorted(hap)[0][
                                0] + "=" + sorted(hap)[1][1] + "," + sorted(hap)[2][0] + "=" + sorted(hap)[0][1]
                    elif dmax == dA or dmax == dD:
                        match = sorted(hap)[0][
                            0] + "=" + sorted(hap)[0][1] + "," + sorted(hap)[2][0] + "=" + sorted(hap)[1][1]
                    else:
                        match = sorted(hap)[0][
                            0] + "=" + sorted(hap)[1][1] + "," + sorted(hap)[2][0] + "=" + sorted(hap)[0][1]
                else:
                    match = "  =  ,  =  "
            else:
                D_prime = "NA"
                r2 = "NA"
                match = "  =  ,  =  "

            snp1 = rsnum_lst[i]
            snp2 = rsnum_lst[j]
            pos1 = pos_lst[i].split("-")[0]
            pos2 = pos_lst[j].split("-")[0]
            allele1 = allele_lst[i]
            allele2 = allele_lst[j]
            corr = match.split(",")[0].split("=")[1] + "=" + match.split(",")[0].split("=")[
                0] + "," + match.split(",")[1].split("=")[1] + "=" + match.split(",")[1].split("=")[0]
            corr_f = match

            ld_matrix[i][j] = [snp1, snp2, allele1,
                               allele2, corr, pos1, pos2, D_prime, r2]
            ld_matrix[j][i] = [snp2, snp1, allele2,
                               allele1, corr_f, pos2, pos1, D_prime, r2]

    # Generate Plot Variables
    out = [j for i in ld_matrix for j in i]
    xnames = []
    ynames = []
    xA = []
    yA = []
    corA = []
    xpos = []
    ypos = []
    D = []
    R = []
    box_color = []
    box_trans = []

    if r2_d not in ["r2", "d"]:
        r2_d = "r2"

    for i in range(len(out)):
        snp1, snp2, allele1, allele2, corr, pos1, pos2, D_prime, r2 = out[i]
        xnames.append(snp1)
        ynames.append(snp2)
        xA.append(allele1)
        yA.append(allele2)
        corA.append(corr)
        xpos.append(pos1)
        ypos.append(pos2)
        if r2_d == "r2" and r2 != "NA":
            D.append(str(round(float(D_prime), 4)))
            R.append(str(round(float(r2), 4)))
            box_color.append("red")
            box_trans.append(r2)
        elif r2_d == "d" and D_prime != "NA":
            D.append(str(round(float(D_prime), 4)))
            R.append(str(round(float(r2), 4)))
            box_color.append("red")
            box_trans.append(abs(D_prime))
        else:
            D.append("NA")
            R.append("NA")
            box_color.append("blue")
            box_trans.append(0.1)

    # Import plotting modules
    from collections import OrderedDict
    from bokeh.embed import components, file_html
    from bokeh.layouts import gridplot
    from bokeh.models import HoverTool, LinearAxis, Range1d
    from bokeh.plotting import ColumnDataSource, curdoc, figure, output_file, reset_output, save
    from bokeh.resources import CDN
    from bokeh.io import export_svgs
    import svgutils.compose as sg
    from math import pi

    reset_output()

    # Aggregate Plotting Data
    x = []
    y = []
    w = []
    h = []
    coord_snps_plot = []
    snp_id_plot = []
    alleles_snp_plot = []
    for i in range(0, len(xpos), int(len(xpos)**0.5)):
        x.append(int(xpos[i].split(":")[1]) / 1000000.0)
        y.append(0.5)
        w.append(0.00003)
        h.append(1.06)
        coord_snps_plot.append(xpos[i])
        snp_id_plot.append(xnames[i])
        alleles_snp_plot.append(xA[i])
    

    buffer = (x[-1] - x[0]) * 0.025
    xr = Range1d(start=x[0] - buffer, end=x[-1] + buffer)
    yr = Range1d(start=-0.03, end=1.03)
    y2_ll = [-0.03] * len(x)
    y2_ul = [1.03] * len(x)

    yr_pos = Range1d(start=(x[-1] + buffer) * -1, end=(x[0] - buffer) * -1)
    yr0 = Range1d(start=0, end=1)
    yr2 = Range1d(start=0, end=3.8)
    yr3 = Range1d(start=0, end=1)

    spacing = (x[-1] - x[0] + buffer + buffer) / (len(x) * 1.0)
    x2 = []
    y0 = []
    y1 = []
    y2 = []
    y3 = []
    y4 = []
    for i in range(len(x)):
        x2.append(x[0] - buffer + spacing * (i + 0.5))
        y0.append(0)
        y1.append(0.20)
        y2.append(0.80)
        y3.append(1)
        y4.append(1.15)

    xname_pos = []
    for i in x2:
        for j in range(len(x2)):
            xname_pos.append(i)

    data = {
            'xname': xnames,
            'xname_pos': xname_pos,
            'yname': ynames,
            'xA': xA,
            'yA': yA,
            'xpos': xpos,
            'ypos': ypos,
            'R2': R,
            'Dp': D,
            'corA': corA,
            'box_color': box_color,
            'box_trans': box_trans
    }

    source = ColumnDataSource(data)

    threshold = 70
    if len(snps) < threshold:
        matrix_plot = figure(outline_line_color="white", min_border_top=0, min_border_bottom=2, min_border_left=100, min_border_right=5,
                             x_range=xr, y_range=list(reversed(rsnum_lst)),
                             h_symmetry=False, v_symmetry=False, border_fill_color='white', x_axis_type=None, logo=None,
                             tools="hover,undo,redo,reset,pan,box_zoom,previewsave", title=" ", plot_width=800, plot_height=700)

    else:
        matrix_plot = figure(outline_line_color="white", min_border_top=0, min_border_bottom=2, min_border_left=100, min_border_right=5,
                             x_range=xr, y_range=list(reversed(rsnum_lst)),
                             h_symmetry=False, v_symmetry=False, border_fill_color='white', x_axis_type=None, y_axis_type=None, logo=None,
                             tools="hover,undo,redo,reset,pan,box_zoom,previewsave", title=" ", plot_width=800, plot_height=700)
    

    matrix_plot.rect(x='xname_pos', y='yname', width=0.95 * spacing, height=0.95, source=source,
                    color="box_color", alpha="box_trans", line_color=None)
    
    matrix_plot.grid.grid_line_color = None
    matrix_plot.axis.axis_line_color = None
    matrix_plot.axis.major_tick_line_color = None
    if len(snps) < threshold:
        matrix_plot.axis.major_label_text_font_size = "8pt"
        matrix_plot.xaxis.major_label_orientation = "vertical"

    matrix_plot.axis.major_label_text_font_style = "normal"
    matrix_plot.xaxis.major_label_standoff = 0

    sup_2 = u"\u00B2"

    hover = matrix_plot.select(dict(type=HoverTool))
    hover.tooltips = OrderedDict([
        ("Variant 1", " " + "@yname (@yA)"),
        ("Variant 2", " " + "@xname (@xA)"),
        ("D\'", " " + "@Dp"),
        ("R" + sup_2, " " + "@R2"),
        ("Correlated Alleles", " " + "@corA"),
    ])

    # Connecting and Rug Plots
    # Connector Plot
    if len(snps) < threshold:
        connector = figure(outline_line_color="white", y_axis_type=None, x_axis_type=None,
                           x_range=xr, y_range=yr2, border_fill_color='white',
                           title="", min_border_left=100, min_border_right=5, min_border_top=0, min_border_bottom=0, h_symmetry=False, v_symmetry=False,
                           plot_width=800, plot_height=90, tools="xpan,tap")
        connector.segment(x, y0, x, y1, color="black")
        connector.segment(x, y1, x2, y2, color="black")
        connector.segment(x2, y2, x2, y3, color="black")
        connector.text(x2, y4, text=snp_id_plot, alpha=1, angle=pi / 2,
                       text_font_size="8pt", text_baseline="middle", text_align="left")
    else:
        connector = figure(outline_line_color="white", y_axis_type=None, x_axis_type=None,
                           x_range=xr, y_range=yr3, border_fill_color='white',
                           title="", min_border_left=100, min_border_right=5, min_border_top=0, min_border_bottom=0, h_symmetry=False, v_symmetry=False,
                           plot_width=800, plot_height=30, tools="xpan,tap")
        connector.segment(x, y0, x, y1, color="black")
        connector.segment(x, y1, x2, y2, color="black")
        connector.segment(x2, y2, x2, y3, color="black")

    connector.yaxis.major_label_text_color = None
    connector.yaxis.minor_tick_line_alpha = 0  # Option does not work
    connector.yaxis.axis_label = " "
    connector.grid.grid_line_color = None
    connector.axis.axis_line_color = None
    connector.axis.major_tick_line_color = None
    connector.axis.minor_tick_line_color = None

    connector.toolbar_location = None

    data_rug = {
        'x': x,
        'y': y,
        'w': w,
        'h': h,
        'coord_snps_plot': coord_snps_plot,
        'snp_id_plot': snp_id_plot,
        'alleles_snp_plot': alleles_snp_plot
    }

    source_rug = ColumnDataSource(data_rug)

    # Rug Plot
    rug = figure(x_range=xr, y_range=yr, y_axis_type=None,
                 title="", min_border_top=1, min_border_bottom=0, min_border_left=100, min_border_right=5, h_symmetry=False, v_symmetry=False,
                 plot_width=800, plot_height=50, tools="hover,xpan,tap")
    rug.rect(x='x', y='y', width='w', height='h', fill_color='red', dilate=True, line_color=None, fill_alpha=0.6, source=source_rug)

    hover = rug.select(dict(type=HoverTool))
    hover.tooltips = OrderedDict([
        ("SNP", "@snp_id_plot (@alleles_snp_plot)"),
        ("Coord", "@coord_snps_plot"),
    ])

    rug.toolbar_location = None

    # Gene Plot
    tabix_gene = "tabix -fh {0} {1}:{2}-{3} > {4}".format(gene_dir, snp_coords[1][1], int(
        (x[0] - buffer) * 1000000), int((x[-1] + buffer) * 1000000), tmp_dir + "genes_" + request + ".txt")
    subprocess.call(tabix_gene, shell=True)
    filename = tmp_dir + "genes_" + request + ".txt"
    genes_raw = open(filename).readlines()

    genes_plot_start = []
    genes_plot_end = []
    genes_plot_y = []
    genes_plot_name = []
    exons_plot_x = []
    exons_plot_y = []
    exons_plot_w = []
    exons_plot_h = []
    exons_plot_name = []
    exons_plot_id = []
    exons_plot_exon = []
    message = ["Too many genes to plot."]
    lines = [0]
    gap = 80000
    tall = 0.75
    if genes_raw != None:
        for i in range(len(genes_raw)):
            bin, name_id, chrom, strand, txStart, txEnd, cdsStart, cdsEnd, exonCount, exonStarts, exonEnds, score, name2, cdsStartStat, cdsEndStat, exonFrames = genes_raw[
                i].strip().split()
            name = name2
            id = name_id
            e_start = exonStarts.split(",")
            e_end = exonEnds.split(",")

            # Determine Y Coordinate
            i = 0
            y_coord = None
            while y_coord == None:
                if i > len(lines) - 1:
                    y_coord = i + 1
                    lines.append(int(txEnd))
                elif int(txStart) > (gap + lines[i]):
                    y_coord = i + 1
                    lines[i] = int(txEnd)
                else:
                    i += 1

            genes_plot_start.append(int(txStart) / 1000000.0)
            genes_plot_end.append(int(txEnd) / 1000000.0)
            genes_plot_y.append(y_coord)
            genes_plot_name.append(name + "  ")

            for i in range(len(e_start) - 1):
                if strand == "+":
                    exon = i + 1
                else:
                    exon = len(e_start) - 1 - i

                width = (int(e_end[i]) - int(e_start[i])) / 1000000.0
                x_coord = int(e_start[i]) / 1000000.0 + (width / 2)

                exons_plot_x.append(x_coord)
                exons_plot_y.append(y_coord)
                exons_plot_w.append(width)
                exons_plot_h.append(tall)
                exons_plot_name.append(name)
                exons_plot_id.append(id)
                exons_plot_exon.append(exon)

    n_rows = len(lines)
    genes_plot_yn = [n_rows - w + 0.5 for w in genes_plot_y]
    exons_plot_yn = [n_rows - w + 0.5 for w in exons_plot_y]
    yr2 = Range1d(start=0, end=n_rows)

    data_gene_plot = {
        'exons_plot_x': exons_plot_x,
        'exons_plot_yn': exons_plot_yn,
        'exons_plot_w': exons_plot_w,
        'exons_plot_h': exons_plot_h,
        'exons_plot_name': exons_plot_name,
        'exons_plot_id': exons_plot_id,
        'exons_plot_exon': exons_plot_exon,
        'coord_snps_plot': coord_snps_plot,
        'snp_id_plot': snp_id_plot,
        'alleles_snp_plot': alleles_snp_plot
    }

    source_gene_plot = ColumnDataSource(data_gene_plot)

    max_genes = 40
    if len(lines) < 3 or len(genes_raw) > max_genes:
        plot_h_pix = 150
    else:
        plot_h_pix = 150 + (len(lines) - 2) * 50

    gene_plot = figure(min_border_top=2, min_border_bottom=0, min_border_left=100, min_border_right=5,
                       x_range=xr, y_range=yr2, border_fill_color='white',
                       title="", h_symmetry=False, v_symmetry=False, logo=None,
                       plot_width=800, plot_height=plot_h_pix, tools="hover,xpan,box_zoom,wheel_zoom,tap,undo,redo,reset,previewsave")

    if len(genes_raw) <= max_genes:
        gene_plot.segment(genes_plot_start, genes_plot_yn, genes_plot_end,
                          genes_plot_yn, color="black", alpha=1, line_width=2)
        gene_plot.rect(x='exons_plot_x', y='exons_plot_yn', width='exons_plot_w', height='exons_plot_h',
                        source=source_gene_plot, fill_color='grey', line_color="grey")
        gene_plot.text(genes_plot_start, genes_plot_yn, text=genes_plot_name, alpha=1, text_font_size="7pt",
                       text_font_style="bold", text_baseline="middle", text_align="right", angle=0)
        hover = gene_plot.select(dict(type=HoverTool))
        hover.tooltips = OrderedDict([
            ("Gene", "@exons_plot_name"),
            ("ID", "@exons_plot_id"),
            ("Exon", "@exons_plot_exon"),
        ])

    else:
        x_coord_text = x[0] + (x[-1] - x[0]) / 2.0
        gene_plot.text(x_coord_text, n_rows / 2.0, text=message, alpha=1,
                       text_font_size="12pt", text_font_style="bold", text_baseline="middle", text_align="center", angle=0)

    gene_plot.xaxis.axis_label = "Chromosome " + \
        snp_coords[1][1] + " Coordinate (Mb)(GRCh37)"
    gene_plot.yaxis.axis_label = "Genes"
    gene_plot.ygrid.grid_line_color = None
    gene_plot.yaxis.axis_line_color = None
    gene_plot.yaxis.minor_tick_line_color = None
    gene_plot.yaxis.major_tick_line_color = None
    gene_plot.yaxis.major_label_text_color = None

    gene_plot.toolbar_location = "below"

    # Change output backend to SVG temporarily for headless export
    # Will be changed back to canvas in LDlink.js
    matrix_plot.output_backend = "svg"
    rug.output_backend = "svg"
    gene_plot.output_backend = "svg"
    export_svgs(matrix_plot, filename=tmp_dir + "matrix_plot_1_" + request + ".svg")
    export_svgs(gene_plot, filename=tmp_dir + "gene_plot_1_" + request + ".svg")

    # Concatenate svgs
    sg.Figure("21.59cm", "27.94cm",
        sg.SVG(tmp_dir + "matrix_plot_1_" + request + ".svg"),
        sg.SVG(tmp_dir + "gene_plot_1_" + request + ".svg").move(0, 720)
        ).save(tmp_dir + "matrix_plot_" + request + ".svg")

    sg.Figure("107.95cm", "139.70cm",
        sg.SVG(tmp_dir + "matrix_plot_1_" + request + ".svg").scale(5),
        sg.SVG(tmp_dir + "gene_plot_1_" + request + ".svg").scale(5).move(0, 3600)
        ).save(tmp_dir + "matrix_plot_scaled_" + request + ".svg")

    # Export to PDF
    subprocess.call("phantomjs ./rasterize.js " + tmp_dir + "matrix_plot_" + request + ".svg " + tmp_dir + "matrix_plot_" + request + ".pdf", shell=True)
    # Export to PNG
    subprocess.call("phantomjs ./rasterize.js " + tmp_dir + "matrix_plot_scaled_" + request + ".svg " + tmp_dir + "matrix_plot_" + request + ".png", shell=True)
    # Export to JPEG
    subprocess.call("phantomjs ./rasterize.js " + tmp_dir + "matrix_plot_scaled_" + request + ".svg " + tmp_dir + "matrix_plot_" + request + ".jpeg", shell=True)    
    # Remove individual SVG files after they are combined
    subprocess.call("rm " + tmp_dir + "matrix_plot_1_" + request + ".svg", shell=True)
    subprocess.call("rm " + tmp_dir + "gene_plot_1_" + request + ".svg", shell=True)
    # Remove scaled SVG file after it is converted to png and jpeg
    subprocess.call("rm " + tmp_dir + "matrix_plot_scaled_" + request + ".svg", shell=True)

    reset_output()

    return None

def main():
    
    # Import LDmatrix options
    if len(sys.argv) == 4:
        snplst = sys.argv[1]
        pop = sys.argv[2]
        request = sys.argv[3]
        r2_d = "r2"
    elif len(sys.argv) == 5:
        snplst = sys.argv[1]
        pop = sys.argv[2]
        request = sys.argv[3]
        r2_d = sys.argv[4]
    else:
        sys.exit()

    # Run function
    calculate_matrix_svg(snplst, pop, request, r2_d)

if __name__ == "__main__":
    main()
