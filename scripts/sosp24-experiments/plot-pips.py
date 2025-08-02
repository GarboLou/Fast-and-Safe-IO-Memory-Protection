
import matplotlib.pyplot as plt
import numpy as np
import re
import glob

flows = ["05", "40"]
bss = ["4k", "8k", "16k", "64k", "256k", "2048k"]
exp_configs = [f"-flow-{f}-fio-{bs}-" for f in flows for bs in bss]

def extract_bs(config):
    match = re.search(r"(4k|8k|16k|64k|256k|2048k)", config)
    return match.group(1) if match else "4k"  # default fallback

def get_ssd_tput(prefix, iommu_str, suffix=""):
    ssd_tputs = {}
    for config in exp_configs:
        bs = extract_bs(config)
        folder = prefix + iommu_str + config + suffix + "-RUN-server-0"
        # filename = f"../../utils/logs/{folder}/fio_bw_read_{bs}_bw.1.log"
        # tputs = []
        # with open(filename, "r") as file:
        #     lines = file.readlines()
        # tputs = [int(line.strip().split(",")[1]) for line in lines]
        # if len(tputs) < 10:
        #     raise ValueError(f"Not enough data points in {filename} to average last 5 lines.")
        # # Take the last 5 lines and extract the second column (value)
        # values = tputs[-7:-2]
        # # Compute the average
        # average = sum(values) / len(values)
        # ssd_tputs[config] = average * 8 / 1000000

        fio_log_prefix = f"../../utils/logs/{folder}/fio_bw_randread_{bs}_bw"
        log_files = glob.glob(fio_log_prefix + ".*")

        if not log_files:
            return

        print(f"Found {len(log_files)} FIO logs to process.")

        total_sum = 0.0
        valid_files = 0

        for logfile in log_files:
            try:
                with open(logfile, "r") as f:
                    lines = f.readlines()
                    values = []
                    for line in lines:
                        parts = [p.strip() for p in line.strip().split(",")]
                        if len(parts) > 1:
                            try:
                                val = int(parts[1])
                                values.append(val)
                            except ValueError:
                                continue
                    if values:
                        avg = sum(values) / len(values)
                        total_sum += avg
                        valid_files += 1
            except Exception as e:
                print(f"Error reading {logfile}: {e}")
        ssd_tputs[config] = total_sum * 8 / 1000000  # Convert to Gbps

    return ssd_tputs


def get_tput(filename):
    with open(filename, "r") as file:
        lines = file.readlines()
    
    # Extract the third number from the second line (index 2)
    if len(lines) > 1:  # Ensure there are at least two lines
        tput = lines[1].strip().split(",")[2]
        # print(tput)
        return float(tput)
    else:
        print("File does not contain enough lines.")


def parse_results(path):
    results = np.genfromtxt(path, dtype=float, delimiter=',', names=True)
    return results

def get_data(prefix, iommu_str, suffix=""):
   
    folders = [
        prefix + iommu_str + config + suffix for config in exp_configs
    ]

    files = [
        "../../utils/reports/" + f + "/tput_metrics.dat" for f in folders
    ]

    data = [
        parse_results(f) for f in files
    ]
    
    return data

def get_data_ring(prefix, iommu_str, suffix=""):
   
    x_labels =  ["0256", "0512", "1024", "2048"]
    folders = [
        prefix + iommu_str + "-ring_buffer-"+ x for x in x_labels
    ]

    files = [
        "../../utils/reports/" + f + "/tput_metrics.dat" for f in folders
    ]

    data = [
        parse_results(f) for f in files
    ]
    
    return data


# def misses_per_page(misses, tput_mean):
#     # a bit of a round-a-bout way from when I used per desc, but it works so not touching it!
#     mbs_per_second = tput_mean * 125
#     descriptors_per_second = mbs_per_second * 4 
#     misses_per_page = misses / descriptors_per_second
#     # GETTING MISSES PER PAGE
#     misses_per_page = misses_per_page / 64
#     return misses_per_page

def misses_per_page(misses, tput_mean):
    # a bit of a round-a-bout way from when I used per desc, but it works so not touching it!
    misses_per_page = misses / (tput_mean * 1000000 / 8 / 4)

    return misses_per_page

def get_misses_per_page(data):
    # tput = data['net_tput_mean']
    acks_page = []
    iotlb_miss_page = []
    l1_miss_page = []
    l2_miss_page = []
    l3_miss_page = []

    # acks_page = misses_per_page(sent_packets, tput)
    for idx in range(len(data)):
        # tp = data[idx]['net_tput_mean']
        tp = data[idx]['pcie_wr_tput_mean']

        iotlb_miss_page.append(misses_per_page(data[idx]['iotlb_misses_mean'], tp))
        l1_miss_page.append(misses_per_page(data[idx]['l1_misses_mean'], tp))
        l2_miss_page.append(misses_per_page(data[idx]['l2_misses_mean'], tp))
        l3_miss_page.append(misses_per_page(data[idx]['l3_misses_mean'], tp))
        acks_page.append(misses_per_page(data[idx]['sent_packets_mean']/20, tp))
    
    return iotlb_miss_page, l1_miss_page, l2_miss_page, l3_miss_page, acks_page

def plot_ssd_tput(iommu_off_data, iommu_on_data, x_labels, title):
    plt.rcParams["font.size"] = 14
    plt.figure(figsize=(14, 7))
    bar_width = 0.35
    # plt.plot(iommu_off_data, iommu_on_data)
    x = np.arange(len(x_labels))
    plt.bar(x - bar_width/2, iommu_off_data, bar_width, label='IOMMU off')
    plt.bar(x + bar_width/2, iommu_on_data, bar_width, label='IOMMU on')

    plt.xlabel("# of flows - block size")

    plt.ylabel("SSD Throughput (Gbps)")
    plt.title(title)
    plt.xticks(x, x_labels)
    plt.legend()

    plt.savefig(title + '.png')
    print('Saved plot to ' + title + '.png')
    plt.close()


def plot_tput(iommu_off_data, iommu_on_data, x_labels, title):
    plt.rcParams["font.size"] = 14
    plt.figure(figsize=(14, 7))
    bar_width = 0.35
    # plt.plot(iommu_off_data, iommu_on_data)
    x = np.arange(len(x_labels))
    plt.bar(x - bar_width/2, iommu_off_data, bar_width, label='IOMMU off')
    plt.bar(x + bar_width/2, iommu_on_data, bar_width, label='IOMMU on')

    plt.xlabel("# of flows - block size")

    plt.ylabel("Throughput (Gbps)")
    plt.title(title + '-NIC')
    plt.xticks(x, x_labels)
    plt.legend()

    plt.savefig(title + '-NIC.png')
    print('Saved plot to ' + title + '-NIC.png')
    plt.close()

def plot_stacked_tput(ssd_off, nic_off, ssd_on, nic_on, x_labels, title):
    plt.rcParams["font.size"] = 14
    plt.figure(figsize=(14, 7))
    bar_width = 0.35
    x = np.arange(len(x_labels))

    # Plot stacked bars for IOMMU off
    plt.bar(x - bar_width/2, ssd_off, bar_width, label='SSD (IOMMU off)', color='skyblue')
    plt.bar(x - bar_width/2, nic_off, bar_width, bottom=ssd_off, label='NIC (IOMMU off)', color='dodgerblue')

    # Plot stacked bars for IOMMU on
    plt.bar(x + bar_width/2, ssd_on, bar_width, label='SSD (IOMMU on)', color='orange')
    plt.bar(x + bar_width/2, nic_on, bar_width, bottom=ssd_on, label='NIC (IOMMU on)', color='darkorange')

    plt.xlabel("# of flows - block size")
    plt.ylabel("Throughput (Gbps)")
    plt.ylim(0, 120)
    plt.title(title)
    plt.xticks(x, x_labels, rotation=0)
    # plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0), borderaxespad=0)
    plt.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, 1.15),  # center top, above figure
        ncol=4,  # number of columns, adjust as needed
        frameon=True,
        fontsize=14
    )
    plt.tight_layout()

    plt.savefig(title + '.png')
    print('Saved plot to ' + title + '.png')
    plt.close()


def plot_stacked_tput_individual(x_labels, title):
    plt.rcParams["font.size"] = 14
    plt.figure(figsize=(14, 7))
    bar_width = 0.35
    x = np.arange(len(x_labels))

    # bss = ["4k", "16k", "64k", "256k", "2048k"]
    ssd_off = [46.732240000000004, 49.75691333333333, 50.16445266666667, 49.93920333333333, 38.276958666666665, 38.26434, 46.732240000000004, 49.75691333333333, 50.16445266666667, 49.93920333333333, 38.276958666666665, 38.26434]
    nic_off = [59.5960000000, 59.5960000000, 59.5960000000, 59.5960000000, 59.5960000000, 59.5960000000, 58.7300000000, 58.7300000000, 58.7300000000, 58.7300000000, 58.7300000000, 58.7300000000]
    ssd_on = [19.152546666666666, 37.530432, 50.226786, 50.956302, 38.268882, 38.259256, 19.152546666666666, 37.530432, 50.226786, 50.956302, 38.268882, 38.259256]
    nic_on = [57.7370000000, 57.7370000000, 57.7370000000, 57.7370000000, 57.7370000000, 57.7370000000, 21.8650000000, 21.8650000000, 21.8650000000, 21.8650000000, 21.8650000000, 21.8650000000]

    # Plot stacked bars for IOMMU off
    plt.bar(x - bar_width/2, ssd_off,  bar_width, label='SSD (IOMMU off)', color='lightgreen')
    plt.bar(x - bar_width/2, nic_off,  bar_width, bottom=ssd_off, label='NIC (IOMMU off)', color='tab:green')

    # Plot stacked bars for IOMMU on using shades of purple
    plt.bar(x + bar_width/2, ssd_on,   bar_width, label='SSD (IOMMU on)', color='plum')
    plt.bar(x + bar_width/2, nic_on,   bar_width, bottom=ssd_on, label='NIC (IOMMU on)', color='tab:purple')

    plt.xlabel("# of flows - block size")
    plt.ylabel("Throughput (Gbps)")
    plt.ylim(0, 120)
    plt.title(title)
    plt.xticks(x, x_labels, rotation=0)
    # plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0), borderaxespad=0)
    plt.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, 1.15),  # center top, above figure
        ncol=4,  # number of columns, adjust as needed
        frameon=True,
        fontsize=14
    )
    plt.tight_layout()

    plt.savefig(title + '.png')
    print('Saved plot to ' + title + '.png')
    plt.close()

def plot_stacked_tput_compare(ssd_off, nic_off, ssd_on, nic_on, x_labels, title):
    plt.rcParams["font.size"] = 14
    plt.figure(figsize=(16, 7))
    bar_width = 0.2
    x = np.arange(len(x_labels))

    individual_ssd_off = [46.732240000000004, 49.75691333333333, 50.16445266666667, 49.93920333333333, 38.276958666666665, 38.26434, 46.732240000000004, 49.75691333333333, 50.16445266666667, 49.93920333333333, 38.276958666666665, 38.26434]
    individual_nic_off = [59.5960000000, 59.5960000000, 59.5960000000, 59.5960000000, 59.5960000000, 59.5960000000, 58.7300000000, 58.7300000000, 58.7300000000, 58.7300000000, 58.7300000000, 58.7300000000]
    individual_ssd_on = [19.152546666666666, 37.530432, 50.226786, 50.956302, 38.268882, 38.259256, 19.152546666666666, 37.530432, 50.226786, 50.956302, 38.268882, 38.259256]
    individual_nic_on = [57.7370000000, 57.7370000000, 57.7370000000, 57.7370000000, 57.7370000000, 57.7370000000, 21.8650000000, 21.8650000000, 21.8650000000, 21.8650000000, 21.8650000000, 21.8650000000]

    # Plot stacked bars for IOMMU off
    plt.bar(x - bar_width/2*3, individual_ssd_off, bar_width, label='SUM(SR) SSD (IOMMU off)', color='lightgreen')
    plt.bar(x - bar_width/2*3, individual_nic_off, bar_width, bottom=individual_ssd_off, label='SUM(SR) (IOMMU off)', color='tab:green')
    plt.bar(x - bar_width/2, ssd_off, bar_width, label='Corun SSD (IOMMU off)', color='skyblue')
    plt.bar(x - bar_width/2, nic_off, bar_width, bottom=ssd_off, label='Corun NIC (IOMMU off)', color='dodgerblue')

    # Plot stacked bars for IOMMU on
    plt.bar(x + bar_width/2, ssd_on, bar_width, label='Corun SSD (IOMMU on)', color='orange')
    plt.bar(x + bar_width/2, nic_on, bar_width, bottom=ssd_on, label='Corun NIC (IOMMU on)', color='darkorange')
    plt.bar(x + bar_width/2*3, individual_ssd_on, bar_width, label='SUM(SR) SSD (IOMMU on)', color='plum')
    plt.bar(x + bar_width/2*3, individual_nic_on, bar_width, bottom=individual_ssd_on, label='SUM(SR) NIC (IOMMU on)', color='tab:purple')

    plt.xlabel("# of flows - block size")
    plt.ylabel("Throughput (Gbps)")
    plt.ylim(0, 120)
    plt.title(title)
    plt.xticks(x, x_labels, rotation=0)
    # plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0), borderaxespad=0)
    plt.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, 1.15),  # center top, above figure
        ncol=4,  # number of columns, adjust as needed
        frameon=True,
        fontsize=14
    )
    plt.tight_layout()

    plt.savefig(title + '.png')
    print('Saved plot to ' + title + '.png')
    plt.close()

def plot_drop_rate(iommu_off_data, iommu_on_data, x_labels, title):
    plt.rcParams["font.size"] = 14
    plt.figure(figsize=(14, 7))
    bar_width = 0.35
    # plt.plot(iommu_off_data, iommu_on_data)
    x = np.arange(len(x_labels))
    plt.bar(x - bar_width/2, iommu_off_data, bar_width, label='IOMMU off')
    plt.bar(x + bar_width/2, iommu_on_data, bar_width, label='IOMMU on')

    plt.xlabel("# of flows - block size")

    plt.ylabel("Drop rate")
    plt.title(title)
    plt.xticks(x, x_labels)
    plt.legend()
    plt.tight_layout()
    plt.savefig(title + '.png')
    print('Saved plot to ' + title + '.png')
    plt.close()

def plot_iommu_misses_stats(iommu_on_data, x_labels, title):
    iotlb_miss_page, l1_miss_page, l2_miss_page, l3_miss_page, acks_page = get_misses_per_page(iommu_on_data)

    plt.rcParams["font.size"] = 14
    plt.figure(figsize=(14, 7))
    bar_width = 0.35
    # plt.plot(iommu_off_data, iommu_on_data)
    x = np.arange(len(x_labels))
    plt.bar(x, iotlb_miss_page, bar_width, label='IOMMU TLB misses')
    # plt.bar(x + bar_width/2, iommu_on_data, bar_width, label='IOMMU on')

    plt.xlabel("# of flows - block size")

    plt.ylabel("IOTLB misses per page")
    plt.title(title + 'IOTLB-miss')
    plt.xticks(x, x_labels)
    plt.legend()
    plt.ylim(0, 4)


    plt.tight_layout()
    file_name = title + 'IOTLB-miss.png'
    plt.savefig(file_name)
    print('Saved plot to ' + file_name)
    plt.close()


    # plot L1, L2, L3 misses

    plt.figure(figsize=(14, 7))
    x = np.arange(len(x_labels))
    plt.bar(x, acks_page, bar_width, label='ACKs per page')
    # plt.bar(x + bar_width/2, iommu_on_data, bar_width, label='IOMMU on')

    plt.xlabel("# of flows - block size")

    plt.ylabel("Acks per page")
    plt.title(title + 'IOTLB-miss')
    plt.xticks(x, x_labels)
    plt.legend()
    plt.ylim(0, 0.15)


    plt.tight_layout()
    file_name = title + 'Acks.png'
    plt.savefig(file_name)
    print('Saved plot to ' + file_name)
    plt.close()


    # plot L1, L2, L3 misses
    plt.figure(figsize=(14, 7))
    bar_width = 0.25

    plt.bar(x - bar_width,  l1_miss_page, bar_width, label='L1')
    plt.bar(x,              l2_miss_page, bar_width, label='L2')
    plt.bar(x + bar_width,  l3_miss_page, bar_width, label='L3')
    
    plt.xlabel("# of flows - block size")

    plt.ylabel("Misses per page")
    plt.title(title + 'L1-L2-L3-miss')
    plt.xticks(x, x_labels)
    plt.legend()
    plt.ylim(0, 0.5)

    plt.tight_layout()
    file_name = title + 'L1-L2-L3-miss.png'
    plt.savefig(file_name)
    print('Saved plot to ' + file_name)
    plt.close()


def plot_all_subplots(iommu_off_all_data, iommu_on_all_data, x_labels, title_key):
    plot_tput(
        iommu_off_data = [ r['net_tput_mean'] for r in iommu_off_all_data ],
        iommu_on_data = [ r['net_tput_mean'] for r in iommu_on_all_data ],
        x_labels = x_labels,
        title = title_key + '-tput'
    )

    plot_drop_rate(
        iommu_off_data = [ r['retx_rate_mean'] for r in iommu_off_all_data ],
        iommu_on_data = [ r['retx_rate_mean'] for r in iommu_on_all_data ],
        x_labels = x_labels,
        title = title_key + '-drop-rate'
    )

    plot_iommu_misses_stats(
        iommu_on_data = iommu_on_all_data,
        x_labels = x_labels,
        title = title_key + '-misses'
    )

def plot_tput_pips():
    x_labels =  [f"{f}-{bs}" for f in flows for bs in bss]
    iommu_off_all_data = get_data(prefix="6.0.3-vanilla-", iommu_str="iommu-off", suffix="pips")
    iommu_on_all_data = get_data(prefix="6.0.3-vanilla-", iommu_str="iommu-on", suffix="pips")

    plot_all_subplots(iommu_off_all_data, iommu_on_all_data, x_labels, 'PIPS-corun')

    iommu_off_ssd_tput = get_ssd_tput(prefix="6.0.3-vanilla-", iommu_str="iommu-off", suffix="pips")
    iommu_on_ssd_tput = get_ssd_tput(prefix="6.0.3-vanilla-", iommu_str="iommu-on", suffix="pips")
    plot_ssd_tput(
        iommu_off_data = iommu_off_ssd_tput.values(),
        iommu_on_data = iommu_on_ssd_tput.values(),
        x_labels = x_labels,
        title = 'PIPS-corun-tput-SSD'
    )

    plot_stacked_tput(
        ssd_off = list(iommu_off_ssd_tput.values()),
        nic_off = [r['net_tput_mean'] for r in iommu_off_all_data],
        ssd_on = list(iommu_on_ssd_tput.values()),
        nic_on = [r['net_tput_mean'] for r in iommu_on_all_data],
        x_labels = x_labels,
        title = 'PIPS-corun-tput-SSD-NIC'
    )

    plot_stacked_tput_individual(x_labels, 'PIPS-individual-run-sum-tput-NIC-SSD')
    plot_stacked_tput_compare(ssd_off = list(iommu_off_ssd_tput.values()),
        nic_off = [r['net_tput_mean'] for r in iommu_off_all_data],
        ssd_on = list(iommu_on_ssd_tput.values()),
        nic_on = [r['net_tput_mean'] for r in iommu_on_all_data],
        x_labels = x_labels,
        title = 'PIPS-compare-corun-tput-SSD-NIC'
    )




plot_tput_pips()

