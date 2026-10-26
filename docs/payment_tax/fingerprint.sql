BEGIN READ ONLY;
SELECT 'payments', count(*), md5(string_agg(concat_ws('|',id,name,date,amount,currency_id,partner_id,state,move_id), ';' ORDER BY id)) FROM account_payment;
SELECT 'journal_entries', count(*), md5(string_agg(concat_ws('|',id,name,date,move_type,state,partner_id,amount_total,amount_residual), ';' ORDER BY id)) FROM account_move;
SELECT 'journal_lines', count(*), md5(string_agg(concat_ws('|',id,move_id,account_id,partner_id,debit,credit,balance,amount_currency,currency_id,tax_line_id,amount_residual), ';' ORDER BY id)) FROM account_move_line;
COMMIT;
