from pathlib import Path

import pandas as pd


class CsvDataTools:
    def __init__(self, csv_path: Path):
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)

    def get_schema_summary(self) -> dict:
        return {
            "file": self.csv_path.name,
            "rows": len(self.df),
            "columns": list(self.df.columns),
            "dtypes": self.df.dtypes.astype(str).to_dict(),
            "missing_values": self.df.isna().sum().to_dict(),
            "sample_rows": self.df.head(5).to_dict(orient="records"),
        }

    def groupby_sum(self, group_col: str, value_col: str, top_n: int = 5) -> dict:
        top_n = int(top_n or 5)

        if group_col not in self.df.columns:
            return {"error": f"Column not found: {group_col}", "available_columns": list(self.df.columns)}

        if value_col not in self.df.columns:
            return {"error": f"Column not found: {value_col}", "available_columns": list(self.df.columns)}

        if not pd.api.types.is_numeric_dtype(self.df[value_col]):
            return {"error": f"Column is not numeric: {value_col}"}

        result = (
            self.df.groupby(group_col, dropna=False)[value_col]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
            .reset_index()
        )

        return {
            "group_col": group_col,
            "value_col": value_col,
            "top_n": top_n,
            "result": result.to_dict(orient="records"),
        }

    def sum_column(self, column: str) -> dict:
        if column not in self.df.columns:
            return {"error": f"Column not found: {column}", "available_columns": list(self.df.columns)}

        if not pd.api.types.is_numeric_dtype(self.df[column]):
            return {"error": f"Column is not numeric: {column}"}

        return {
            "column": column,
            "sum": float(self.df[column].sum()),
        }

    def describe_column(self, column: str) -> dict:
        if column not in self.df.columns:
            return {"error": f"Column not found: {column}", "available_columns": list(self.df.columns)}

        series = self.df[column]

        if pd.api.types.is_numeric_dtype(series):
            return {
                "column": column,
                "type": "numeric",
                "count": int(series.count()),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "min": float(series.min()),
                "max": float(series.max()),
            }

        return {
            "column": column,
            "type": "categorical",
            "count": int(series.count()),
            "unique_count": int(series.nunique()),
            "top_values": series.value_counts(dropna=False).head(10).to_dict(),
        }

    def count_by_column(self, column: str, top_n: int = 10) -> dict:
        top_n = int(top_n or 10)

        if column not in self.df.columns:
            return {"error": f"Column not found: {column}", "available_columns": list(self.df.columns)}

        result = self.df[column].value_counts(dropna=False).head(top_n).reset_index()
        result.columns = [column, "count"]

        return {
            "column": column,
            "top_n": top_n,
            "result": result.to_dict(orient="records"),
        }
    def missing_report(self) -> dict:
        missing = self.df.isna().sum()
        missing_rate = self.df.isna().mean()

        result = []
        for column in self.df.columns:
            if missing[column] > 0:
                result.append({
                    "column": column,
                    "missing_count": int(missing[column]),
                    "missing_rate": float(missing_rate[column]),
                })

        return {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "total_missing_values": int(missing.sum()),
            "columns_with_missing_values": result,
            "duplicate_rows": int(self.df.duplicated().sum()),
        }

    def numeric_summary(self) -> dict:
        numeric_df = self.df.select_dtypes(include="number")

        if numeric_df.empty:
            return {"error": "No numeric columns found."}

        summary = numeric_df.describe().T.reset_index()
        summary = summary.rename(columns={"index": "column"})

        return {
            "numeric_columns": list(numeric_df.columns),
            "summary": summary.to_dict(orient="records"),
        }

    def categorical_summary(self, top_n: int = 5) -> dict:
        top_n = int(top_n or 5)
        categorical_df = self.df.select_dtypes(include=["object", "category", "bool"])

        if categorical_df.empty:
            return {"error": "No categorical columns found."}

        result = []
        for column in categorical_df.columns:
            top_values = categorical_df[column].value_counts(dropna=False).head(top_n).to_dict()
            result.append({
                "column": column,
                "unique_count": int(categorical_df[column].nunique(dropna=False)),
                "top_values": top_values,
            })

        return {
            "categorical_columns": list(categorical_df.columns),
            "top_n": top_n,
            "summary": result,
        }

    def correlation_report(self, target_col: str | None = None, top_n: int = 10) -> dict:
        top_n = int(top_n or 10)
        numeric_df = self.df.select_dtypes(include="number")

        if numeric_df.shape[1] < 2:
            return {"error": "At least two numeric columns are required for correlation analysis."}

        corr = numeric_df.corr(numeric_only=True)

        if target_col:
            if target_col not in numeric_df.columns:
                return {
                    "error": f"Target column is not numeric or does not exist: {target_col}",
                    "numeric_columns": list(numeric_df.columns),
                }

            target_corr = (
                corr[target_col]
                .drop(labels=[target_col])
                .dropna()
                .sort_values(key=lambda s: s.abs(), ascending=False)
                .head(top_n)
            )

            return {
                "target_col": target_col,
                "top_n": top_n,
                "correlations": target_corr.to_dict(),
            }

        pairs = []
        columns = list(corr.columns)
        for i, col_a in enumerate(columns):
            for col_b in columns[i + 1:]:
                value = corr.loc[col_a, col_b]
                if pd.notna(value):
                    pairs.append({
                        "column_a": col_a,
                        "column_b": col_b,
                        "correlation": float(value),
                        "abs_correlation": abs(float(value)),
                    })

        pairs = sorted(pairs, key=lambda item: item["abs_correlation"], reverse=True)[:top_n]

        return {
            "top_n": top_n,
            "correlation_pairs": pairs,
        }
    def eda_overview(self) -> dict:
        return {
            "schema": self.get_schema_summary(),
            "missing_report": self.missing_report(),
            "numeric_summary": self.numeric_summary(),
            "categorical_summary": self.categorical_summary(top_n=5),
            "correlation_report": self.correlation_report(top_n=10),
        }
    def business_kpi_overview(
        self,
        sales_col: str = "Sales",
        quantity_col: str = "Quantity",
        profit_col: str = "gross income",
        rating_col: str = "Rating",
    ) -> dict:
        result = {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "order_count": len(self.df),
        }

        if sales_col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[sales_col]):
            result["sales_col"] = sales_col
            result["total_sales"] = float(self.df[sales_col].sum())
            result["avg_order_value"] = float(self.df[sales_col].mean())
            result["min_order_value"] = float(self.df[sales_col].min())
            result["max_order_value"] = float(self.df[sales_col].max())

        if quantity_col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[quantity_col]):
            result["quantity_col"] = quantity_col
            result["total_quantity"] = float(self.df[quantity_col].sum())
            result["avg_quantity_per_order"] = float(self.df[quantity_col].mean())

        if profit_col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[profit_col]):
            result["profit_col"] = profit_col
            result["total_profit"] = float(self.df[profit_col].sum())
            result["avg_profit_per_order"] = float(self.df[profit_col].mean())

        if rating_col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[rating_col]):
            result["rating_col"] = rating_col
            result["avg_rating"] = float(self.df[rating_col].mean())

        return result

    def category_performance(
        self,
        group_col: str,
        sales_col: str = "Sales",
        quantity_col: str = "Quantity",
        profit_col: str = "gross income",
        rating_col: str = "Rating",
        top_n: int = 10,
    ) -> dict:
        top_n = int(top_n or 10)

        if group_col not in self.df.columns:
            return {"error": f"Column not found: {group_col}", "available_columns": list(self.df.columns)}

        if sales_col not in self.df.columns or not pd.api.types.is_numeric_dtype(self.df[sales_col]):
            return {"error": f"Sales column is not numeric or does not exist: {sales_col}"}

        grouped = self.df.groupby(group_col, dropna=False)

        result = grouped.agg(
            order_count=(sales_col, "size"),
            total_sales=(sales_col, "sum"),
            avg_order_value=(sales_col, "mean"),
        )

        total_sales = self.df[sales_col].sum()
        result["sales_share"] = result["total_sales"] / total_sales if total_sales else 0

        if quantity_col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[quantity_col]):
            result["total_quantity"] = grouped[quantity_col].sum()

        if profit_col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[profit_col]):
            result["total_profit"] = grouped[profit_col].sum()

        if rating_col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[rating_col]):
            result["avg_rating"] = grouped[rating_col].mean()

        result = result.sort_values("total_sales", ascending=False).head(top_n).reset_index()

        return {
            "group_col": group_col,
            "sales_col": sales_col,
            "top_n": top_n,
            "result": result.to_dict(orient="records"),
        }

    def time_trend(
        self,
        date_col: str = "Date",
        value_col: str = "Sales",
        freq: str = "D",
        top_n: int = 10,
    ) -> dict:
        top_n = int(top_n or 10)

        if date_col not in self.df.columns:
            return {"error": f"Date column not found: {date_col}", "available_columns": list(self.df.columns)}

        if value_col not in self.df.columns or not pd.api.types.is_numeric_dtype(self.df[value_col]):
            return {"error": f"Value column is not numeric or does not exist: {value_col}"}

        parsed_dates = pd.to_datetime(self.df[date_col], errors="coerce")
        valid_df = self.df.loc[parsed_dates.notna()].copy()
        valid_df["_parsed_date"] = parsed_dates[parsed_dates.notna()]

        if valid_df.empty:
            return {"error": f"Could not parse any valid dates from column: {date_col}"}

        trend = (
            valid_df.set_index("_parsed_date")[value_col]
            .resample(freq)
            .agg(["count", "sum", "mean"])
            .reset_index()
        )

        trend.columns = ["period", "order_count", "total_value", "avg_value"]
        trend["period"] = trend["period"].dt.strftime("%Y-%m-%d")

        top_periods = trend.sort_values("total_value", ascending=False).head(top_n)

        return {
            "date_col": date_col,
            "value_col": value_col,
            "freq": freq,
            "period_count": len(trend),
            "first_period": trend["period"].iloc[0],
            "last_period": trend["period"].iloc[-1],
            "trend_sample": trend.head(top_n).to_dict(orient="records"),
            "top_periods": top_periods.to_dict(orient="records"),
            "trend": trend.to_dict(orient="records"),
        }

    def call_tool(self, tool_name: str, tool_args: dict) -> dict:
        available_tools = {
            "get_schema_summary": self.get_schema_summary,
            "groupby_sum": self.groupby_sum,
            "sum_column": self.sum_column,
            "describe_column": self.describe_column,
            "count_by_column": self.count_by_column,
            "missing_report": self.missing_report,
            "numeric_summary": self.numeric_summary,
            "categorical_summary": self.categorical_summary,
            "correlation_report": self.correlation_report,
            "eda_overview": self.eda_overview,
            "business_kpi_overview": self.business_kpi_overview,
            "category_performance": self.category_performance,
            "time_trend": self.time_trend,
        }

        if tool_name not in available_tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        return available_tools[tool_name](**tool_args)


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_schema_summary",
            "description": "Inspect the CSV table schema, column types, missing values, and sample rows.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "groupby_sum",
            "description": "Group by one column and sum a numeric column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_col": {"type": "string"},
                    "value_col": {"type": "string"},
                    "top_n": {"type": "integer"},
                },
                "required": ["group_col", "value_col"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sum_column",
            "description": "Calculate the total sum of a numeric column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                },
                "required": ["column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_column",
            "description": "Describe a numeric or categorical column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                },
                "required": ["column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_by_column",
            "description": "Count the frequency of values in a categorical column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                    "top_n": {"type": "integer"},
                },
                "required": ["column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "missing_report",
            "description": (
                "Analyze missing values and duplicate rows in the CSV dataset. "
                "Use this when the user asks about missing values, null values, data completeness, or duplicate rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "numeric_summary",
            "description": (
                "Summarize all numeric columns with count, mean, standard deviation, min, quartiles, and max. "
                "Use this when the user asks for all numeric fields, numeric overview, descriptive statistics, or statistical summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "categorical_summary",
            "description": (
                "Summarize categorical columns with unique counts and top frequent values. "
                "Use this when the user asks about categorical fields, category distribution, value counts, or class distribution."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top frequent values to return for each categorical column.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "correlation_report",
            "description": (
                "Analyze Pearson correlations between numeric columns. "
                "If target_col is provided, return the numeric columns most correlated with that target. "
                "Use this when the user asks about correlation, relationships between numeric fields, or which fields are related to a target metric."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target_col": {
                        "type": "string",
                        "description": "Optional numeric target column, such as Sales or Rating.",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of strongest correlations to return.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eda_overview",
            "description": "Run a complete exploratory data analysis overview, including schema, missing values, numeric summary, categorical summary, and correlation report. Use this when the user asks for an overall analysis of the dataset.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "business_kpi_overview",
            "description": (
                "Calculate core business KPIs such as total sales, order count, average order value, "
                "total quantity, total profit, and average rating. Use this for business overview or KPI questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sales_col": {"type": "string"},
                    "quantity_col": {"type": "string"},
                    "profit_col": {"type": "string"},
                    "rating_col": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "category_performance",
            "description": (
                "Analyze business performance by a categorical column, such as City, Product line, "
                "Payment, Customer type, Gender, or Branch. Returns order count, total sales, sales share, "
                "average order value, total quantity, total profit, and average rating."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "group_col": {"type": "string"},
                    "sales_col": {"type": "string"},
                    "quantity_col": {"type": "string"},
                    "profit_col": {"type": "string"},
                    "rating_col": {"type": "string"},
                    "top_n": {"type": "integer"},
                },
                "required": ["group_col"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "time_trend",
            "description": (
                "Analyze sales or numeric value trend over time. Use this for daily, weekly, monthly, "
                "date-based, or trend analysis questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date_col": {"type": "string"},
                    "value_col": {"type": "string"},
                    "freq": {
                        "type": "string",
                        "description": "Pandas frequency, such as D for daily, W for weekly, M for monthly.",
                    },
                    "top_n": {"type": "integer"},
                },
            },
        },
    },
]