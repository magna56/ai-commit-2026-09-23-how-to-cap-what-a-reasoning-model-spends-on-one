# How to Cap What a Reasoning Model Spends on One Request

**TL;DR:** An effort level shifts how much a model thinks. It never bounds it, and the only enforced ceiling truncates the request mid-thought while still billing you for the thinking.

Published from [The AI Commit](https://theaicommit.com/#2026-09-23/code) — New Models & APIs, 2026-09-23.

## Run

```bash
python3 code_example.py
```

## Output

```
4000 requests per effort level, seed 3

effort       median      p95      p99      max   spread
-------------------------------------------------------
minimal         266      549      784    1,635     2.9x
low             745    2,027    3,010    8,600     4.0x
medium        1,775    6,212   10,342   33,858     5.8x
high          4,031   18,087   32,397  105,461     8.0x

The spread column is the point: one effort level is not one cost.
At 'high', the slowest one percent of requests think 8x more than the median one.

Choosing a cap for 'medium' at a 2% truncation budget
  max_output_tokens = 8,895   (p98 of reasoning, plus 400 for the answer)

      cap   truncated   tokens paid for nothing   cost of that
--------------------------------------------------------------
    2,048      54.3%                 4,350,132          $5.22
    4,096      17.5%                 2,843,998          $3.41
    8,192       2.7%                   888,696          $1.07
    8,895       2.0%                   709,704          $0.85  <- chosen
   32,768       0.1%                    65,208          $0.08

A round number is a guess about a distribution you have already logged.
Every row above is the same model on the same work. Only the ceiling moved.

```

## Code

See [`code_example.py`](code_example.py).
