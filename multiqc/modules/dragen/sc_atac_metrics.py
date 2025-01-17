import logging
import re

from multiqc.modules.base_module import BaseMultiqcModule
from multiqc.modules.dragen.utils import Metric, make_headers
from multiqc.plots import table

log = logging.getLogger(__name__)

METRIC_NAMES = [
    "Unique cell-barcodes",
    "Fragment threshold for passing cells",
    "Passing cells",
    "Median fragments per cell",
    "Median peaks per cell",
    "Total peaks detected",
]
METRICS = [
    Metric(
        id=m,
        title=" ".join([w.title() if w.islower() else w for w in m.split()]),
        in_genstats="#",
        in_own_tabl="#",
        precision=0,
        descr=m
    )
    for m in METRIC_NAMES
]


class DragenScAtacMetrics(BaseMultiqcModule):
    def add_sc_atac_metrics(self):
        data_by_sample = dict()

        for f in self.find_log_files("dragen/sc_atac_metrics"):
            data = parse_scatac_metrics_file(f)
            if f["s_name"] in data_by_sample:
                log.debug("Duplicate sample name found! Overwriting: {}".format(f["s_name"]))
            self.add_data_source(f, section="stats")
            data_by_sample[f["s_name"]] = data

        # Filter to strip out ignored sample names:
        data_by_sample = self.ignore_samples(data_by_sample)

        if not data_by_sample:
            return set()

        gen_stats_headers, table_headers = make_headers(METRIC_NAMES, METRICS)

        self.general_stats_addcols(data_by_sample, gen_stats_headers)
        self.add_section(
            name="Single-Cell ATAC Metrics",
            anchor="sc-atac-metrics",
            description="""
            Summary metrics for single-cell ATAC.
            """,
            plot=table.plot(
                {
                    sample_name: {
                        metric_name: int(stat) for metric_name, stat in metric.items() if metric_name in METRIC_NAMES
                    }
                    for sample_name, metric in data_by_sample.items()
                },
                table_headers,
            ),
        )

        return data_by_sample.keys()


def parse_scatac_metrics_file(f):
    """
    sample.scATAC.metrics.csv

    SINGLE-CELL ATAC METRICS,LP1339_MultiomeATAC_Donor1_A1,Invalid barcode fragments,0
    SINGLE-CELL ATAC METRICS,LP1339_MultiomeATAC_Donor1_A1,Error free cell-barcode,21805716
    SINGLE-CELL ATAC METRICS,LP1339_MultiomeATAC_Donor1_A1,Error corrected cell-barcode,772423
    SINGLE-CELL ATAC METRICS,LP1339_MultiomeATAC_Donor1_A1,Filtered cell-barcode,577454
    SINGLE-CELL ATAC METRICS,LP1339_MultiomeATAC_Donor1_A1,Fragments passing filters,19368510
    """
    f["s_name"] = re.search(r"(.*).scATAC.metrics.csv", f["fn"]).group(1)

    data = {}
    for line in f["f"].splitlines():
        tokens = line.split(",")
        if len(tokens) == 4:
            analysis, _, metric, stat = tokens
            percentage = None
        elif len(tokens) == 5:
            analysis, _, metric, stat, percentage = tokens
        else:
            raise ValueError(f"Unexpected number of tokens in line {line}")

        try:
            stat = float(stat)
        except ValueError:
            pass
        data[metric] = stat

    return data
