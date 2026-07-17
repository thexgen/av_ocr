                 React UI
                     │
                     ▼
            Upload Holding File
                     │
                     ▼
               API Gateway
                     │
                     ▼
             Python Lambda
                     │
                     ▼
            Upload Original File
                 to S3 Bucket
                     │
                     ▼
            Generate Job ID
                     │
                     ▼
        Async Processing Starts
                     │
         ┌───────────┼────────────┐
         ▼           ▼            ▼
     Excel       Text PDF    Image PDF
     Pandas      PyMuPDF     PaddleOCR
         │           │            │
         └───────────┴────────────┘
                     │
             Extract Raw Data
                     │
                     ▼
          Python Rule Engine
                     │
        Fully mapped?
          │               │
         YES             NO
          │               │
          ▼               ▼
      Validation       Qwen
                          │
                    Semantic Mapping
                          │
                          ▼
                   Mapping Response
                          │
                          ▼
              Python Final Mapping
                          │
                          ▼
              Validation Engine
                          │
                          ▼
      holding_YYYYMMDD.csv
                          │
                          ▼
          Upload CSV to S3 Bucket
                          │
                          ▼
      Batch Insert TempHolding
                          │
                          ▼
             React Review Screen
                          │
               Process Selected
                          │
                          ▼
        Batch Insert Holdings Table 