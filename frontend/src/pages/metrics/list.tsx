import { useEffect, useState, useMemo } from "react";
import { IResourceComponentsProps } from "@refinedev/core";
import { TextField, useTable } from "@refinedev/antd";
import { Table } from "antd";
import ParentSize from "@visx/responsive/lib/components/ParentSize";
import { IMetric } from "./../../interfaces";
import TimeSeries from "./../../components/TimeSeries/TimeSeries";
import Scatterplot from "./../../components/Scatterplot/Scatterplot";
import { ArrowChart } from "./../../components/ArrowChart/ArrowChart";
import ConfidenceLevel from "./../../components/ConfidenceLevel/ConfidenceLevel";
import { DownOutlined } from "@ant-design/icons";
import { Dropdown, Menu } from "antd";
import { instance } from "./../../axiosInstance";

const SaturationColumns: { dataIndex: string; title: string }[] = [
  { dataIndex: "saturation_3_months", title: "3 months" },
  { dataIndex: "saturation_6_months", title: "6 months" },
  { dataIndex: "saturation_12_months", title: "12 months" },
];

const arrayDifference = (arr1: string[], arr2: string[]) => {
  return arr1.filter((item) => !arr2.includes(item));
};

export const MetricList: React.FC<IResourceComponentsProps> = () => {
  const [saturationColumnIndex, setSaturationColumnIndex] = useState<number>(0);

  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>();

  const { tableProps } = useTable<IMetric>({
    initialSorter: [
      {
        field: "current_saturation",
        order: "desc",
      },
    ],
  });

  const dataSource = tableProps?.dataSource?.map((val, ind) => ({
    ...val,
    key: ind,
  }));

  const [expandedRowUUID, setExpandedRowUUID] = useState<string[]>([]);
  const [timeSeriesDataUUID, setTimeSeriesDataUUID] = useState<string[]>([]);
  const [timeSeriesData, setTimeSeriesData] = useState<Record<string, any>>({});

  useEffect(() => {
    const getData = async (uuid: string) => {
      const { data } = await instance.get(`/predictions/${uuid}`);

      if (data) {
        setTimeSeriesData({ ...timeSeriesData, [uuid]: data });
        setTimeSeriesDataUUID([...timeSeriesDataUUID, uuid]);
      }
    };

    if (expandedRowUUID.length > 0) {
      const newExpandedRows = arrayDifference(
        expandedRowUUID,
        timeSeriesDataUUID
      );
      if (newExpandedRows.length > 0) {
        newExpandedRows.forEach((uuid: string) => getData(uuid));
      }
    }
  }, [expandedRowUUID, timeSeriesDataUUID, timeSeriesData]);

  const menu = (
    <Menu
      items={[
        {
          label: (
            <span onClick={() => setSaturationColumnIndex(0)}>3 months</span>
          ),
          key: 0,
        },
        {
          label: (
            <span onClick={() => setSaturationColumnIndex(1)}>6 months</span>
          ),
          key: 1,
        },
        {
          label: (
            <span onClick={() => setSaturationColumnIndex(2)}>12 months</span>
          ),
          key: 2,
        },
      ]}
    />
  );

  const sortedDataSource = useMemo(() => {
    return dataSource?.sort((a, b) => {
      // Display the selected row first
      if (selectedRowKeys && selectedRowKeys?.length > 0) {
        if (selectedRowKeys && a.key === selectedRowKeys[0]) return -1;
        if (selectedRowKeys && b.key === selectedRowKeys[0]) return 1;
      }
      return 0;
    });
  }, [selectedRowKeys, dataSource]);

  return (
    <>
      <div
        style={{
          width: "100%",
          height: "min(50vh, 250px)",
          position: "relative",
          margin: "5px 5px 5px 5px",
        }}
      >
        <ParentSize>
          {({ width, height }) => (
            <Scatterplot
              data={dataSource
                ?.filter(
                  (datum: any) =>
                    datum["days_to_full"] && datum["days_to_full"] < 1000
                )
                .map((datum: any) => ({
                  ...datum,
                  neg_days_to_full: -1 * datum["days_to_full"],
                }))}
              width={width}
              height={height}
              selectedRowKeys={selectedRowKeys}
              setSelectedRowKeys={setSelectedRowKeys}
            />
          )}
        </ParentSize>
      </div>
      <br />
      <Table
        expandable={{
          onExpand: (expanded, record) => {
            if (expanded) {
              setExpandedRowUUID([...expandedRowUUID, record.uuid]);
            }
          },
          expandedRowRender: (record) => {
            if (
              !Object.prototype.hasOwnProperty.call(timeSeriesData, record.uuid)
            ) {
              return <div>loading...</div>;
            }
            return (
              <div
                style={{
                  width: "95%",
                  height: "min(30vh, 400px)",
                  position: "relative",
                  margin: "5px 10px 40px 20px",
                }}
              >
                {record ? (
                  <ParentSize>
                    {({ width, height }) => {
                      return (
                        <TimeSeries
                          record={timeSeriesData[record.uuid]}
                          width={width}
                          height={height}
                        />
                      );
                    }}
                  </ParentSize>
                ) : (
                  <div>loading...</div>
                )}
              </div>
            );
          },
        }}
        dataSource={sortedDataSource}
        size="small"
        rowSelection={{
          selectedRowKeys,
          onChange: (selectedRowKeys: React.Key[], selectedRows: any) => {
            setSelectedRowKeys(selectedRowKeys);
          },
          type: "radio",
        }}
      >
        <Table.Column
          dataIndex="days_to_full"
          key="days_to_full"
          title="Days until full"
          render={(value) => (
            <TextField
              value={Number.isFinite(value) && value < 1000 ? value : "+300"}
            />
          )}
          sorter={{
            compare: (a: any, b: any) =>
              Number.isFinite(a.days_to_full) && Number.isFinite(b.days_to_full)
                ? a.days_to_full - b.days_to_full
                : a.days_to_full
                ? -1
                : 1,
            multiple: 3,
          }}
        />
        <Table.Column
          dataIndex={SaturationColumns[saturationColumnIndex].dataIndex}
          key={SaturationColumns[saturationColumnIndex].dataIndex}
          title={() => (
            <Dropdown overlay={menu}>
              <span
                onClick={(e) => {
                  e.preventDefault();
                }}
              >
                Saturation in {SaturationColumns[saturationColumnIndex].title}
                {"  "}
                <DownOutlined />
              </span>
            </Dropdown>
          )}
          render={(value) => (
            <ParentSize>
              {() => (
                <ArrowChart
                  width={300}
                  height={50}
                  currentSaturation={value.current_saturation}
                  forecast={value.forecast}
                />
              )}
            </ParentSize>
          )}
        />
        <Table.Column
          dataIndex="confidence_level"
          key="confidence_level"
          title="Confidence Level"
          render={(value) => <ConfidenceLevel confidenceLevel={value} />}
          sorter={{
            compare: (a: any, b: any) =>
              Number.isFinite(a.confidence_level) &&
              Number.isFinite(b.confidence_level)
                ? a.confidence_level - b.confidence_level
                : a.confidence_level
                ? -1
                : 1,
            multiple: 3,
          }}
        />
        <Table.Column
          dataIndex="host_name"
          key="host_name"
          title="Host Name"
          render={(value) => <TextField value={value} />}
          sorter={{
            compare: (a: any, b: any) =>
              a.host_name === b.host_name
                ? 0
                : a.host_name > b.host_name
                ? 1
                : -1,
            multiple: 2,
          }}
        />
        <Table.Column
          dataIndex="service_name"
          key="service_name"
          title="Service"
          render={(value) => <TextField value={value} />}
          sorter={{
            compare: (a: any, b: any) =>
              a.service_name === b.service_name
                ? 0
                : a.service_name > b.service_name
                ? 1
                : -1,
            multiple: 4,
          }}
        />
        <Table.Column
          dataIndex="metric_name"
          key="metric_name"
          title="Metric"
          render={(value) => <TextField value={value} />}
          sorter={{
            compare: (a: any, b: any) =>
              a.metric_name === b.metric_name
                ? 0
                : a.metric_name > b.metric_name
                ? 1
                : -1,
            multiple: 4,
          }}
        />
      </Table>
    </>
  );
};
