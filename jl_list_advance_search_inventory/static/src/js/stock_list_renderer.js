/** @odoo-module **/

import { StockListRenderer } from "@stock/views/stock_empty_list_help";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { DateTimeInputPicker } from '@jl_list_advance_search/js/datetime_input_picker';

StockListRenderer.components['DateTimeInputPicker'] = DateTimeInputPicker;
StockListRenderer.components['MultiRecordSelector'] = MultiRecordSelector;
