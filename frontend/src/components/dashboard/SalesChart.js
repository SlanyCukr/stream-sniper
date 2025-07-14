import {
    Card,
} from 'react-bootstrap'
import Chart from 'react-apexcharts'

const SalesChart = () => {
    const chartoptions = {
        series: [
            {
                name: 'Iphone 13',
                data: [
                    0,
                    31,
                    40,
                    28,
                    51,
                    42,
                    109,
                    100,
                ],
            },
            {
                name: 'Oneplue 9',
                data: [
                    0,
                    11,
                    32,
                    45,
                    32,
                    34,
                    52,
                    41,
                ],
            },
        ],
        options: {
            chart: {
                type: 'area',
            },
            dataLabels: {
                enabled: false,
            },
            grid: {
                strokeDashArray: 3,
            },

            stroke: {
                curve: 'smooth',
                width: 1,
            },
            xaxis: {
                categories: [
                    'Jan',
                    'Feb',
                    'March',
                    'April',
                    'May',
                    'June',
                    'July',
                    'Aug',
                ],
            },
        },
    }
    return (
        <Card>
            <Card.Body>
                <Card.Title as="h3">Sales Summary</Card.Title>
                <Card.Subtitle
                    className="text-muted"
                    as="p">
          Yearly Sales Report
                </Card.Subtitle>
                <Chart
                    type="area"
                    width="100%"
                    height="390"
                    options={chartoptions.options}
                    series={chartoptions.series}
                    aria-label="Sales summary chart showing iPhone 13 and OnePlus 9 sales data by month"
                ></Chart>
            </Card.Body>
        </Card>
    )
}

export default SalesChart
