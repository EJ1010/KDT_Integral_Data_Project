$ErrorActionPreference = 'Stop'

$reportRoot = 'C:\Users\user\Desktop\KDT_2026\프로젝트\02_데이터_프로젝트\03_code\04_PowerBI\.pbix_work_20261103\extracted\Report'
$definitionRoot = Join-Path $reportRoot 'definition'
$pagesRoot = Join-Path $definitionRoot 'pages'
$visualSchema = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json'
$pageSchema = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json'

function Write-JsonFile {
    param([string]$Path, [object]$Value)
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $json = $Value | ConvertTo-Json -Depth 100 -Compress
    [System.IO.File]::WriteAllText($Path, $json, [System.Text.UTF8Encoding]::new($false))
}

function New-Literal {
    param([string]$Value)
    return @{ expr = @{ Literal = @{ Value = $Value } } }
}

function New-SolidColor {
    param([string]$Hex)
    return @{ solid = @{ color = @{ expr = @{ Literal = @{ Value = "'$Hex'" } } } } }
}

function New-ColumnField {
    param([string]$Table, [string]$Column)
    return @{ Column = @{ Expression = @{ SourceRef = @{ Entity = $Table } }; Property = $Column } }
}

function New-AggregationField {
    param([string]$Table, [string]$Column, [int]$Function = 0)
    return @{ Aggregation = @{ Expression = @{ Column = @{ Expression = @{ SourceRef = @{ Entity = $Table } }; Property = $Column } }; Function = $Function } }
}

function New-ExtensionMeasureField {
    param([string]$Table, [string]$Measure)
    return @{ Measure = @{ Expression = @{ SourceRef = @{ Schema = 'extension'; Entity = $Table } }; Property = $Measure } }
}

function New-CategoricalFilter {
    param([string]$Name, [string]$Table, [string]$Column, [string]$Value, [string]$Alias = 'f')
    return @{
        name = $Name
        field = New-ColumnField $Table $Column
        type = 'Categorical'
        filter = @{
            Version = 2
            From = @(@{ Name = $Alias; Entity = $Table; Type = 0 })
            Where = @(@{
                Condition = @{
                    In = @{
                        Expressions = @(@{ Column = @{ Expression = @{ SourceRef = @{ Source = $Alias } }; Property = $Column } })
                        Values = ,@(@{ Literal = @{ Value = "'$Value'" } })
                    }
                }
            })
        }
        howCreated = 'User'
    }
}

function New-TextBox {
    param(
        [string]$Name, [double]$X, [double]$Y, [double]$Width, [double]$Height,
        [string[]]$Lines, [string]$FontSize = '18px', [string]$Color = '#202124',
        [string]$FontFamily = 'Segoe UI', [string]$FontWeight = 'normal',
        [string]$Alignment = 'left', [int]$TabOrder = 0
    )
    $paragraphs = @()
    foreach ($line in $Lines) {
        $paragraphs += @{
            textRuns = @(@{
                value = $line
                textStyle = @{
                    fontFamily = $FontFamily
                    fontSize = $FontSize
                    color = $Color
                    fontWeight = $FontWeight
                }
            })
            horizontalTextAlignment = $Alignment
        }
    }
    return @{
        '$schema' = $visualSchema
        name = $Name
        position = @{ x = $X; y = $Y; z = 1000; width = $Width; height = $Height; tabOrder = $TabOrder }
        visual = @{
            visualType = 'textbox'
            objects = @{ general = @(@{ properties = @{ paragraphs = $paragraphs } }) }
            visualContainerObjects = @{
                background = @(@{ properties = @{ show = New-Literal 'false' } })
                border = @(@{ properties = @{ show = New-Literal 'false' } })
                padding = @(@{ properties = @{
                    top = New-Literal '0D'; bottom = New-Literal '0D'; left = New-Literal '0D'; right = New-Literal '0D'
                } })
            }
        }
    }
}

function New-Image {
    param(
        [string]$Name, [double]$X, [double]$Y, [double]$Width, [double]$Height,
        [string]$ItemName, [int]$TabOrder = 0
    )
    return @{
        '$schema' = $visualSchema
        name = $Name
        position = @{ x = $X; y = $Y; z = 0; width = $Width; height = $Height; tabOrder = $TabOrder }
        visual = @{
            visualType = 'image'
            objects = @{
                general = @(@{
                    properties = @{
                        imageUrl = @{
                            expr = @{
                                ResourcePackageItem = @{
                                    PackageName = 'RegisteredResources'
                                    PackageType = 1
                                    ItemName = $ItemName
                                }
                            }
                        }
                    }
                })
            }
            drillFilterOtherVisuals = $true
        }
    }
}

function New-BarChart {
    param(
        [string]$Name, [double]$X, [double]$Y, [double]$Width, [double]$Height,
        [string]$Table, [string]$CategoryColumn, [string]$ValueColumn,
        [string]$MeasureName = '', [string]$Color = '#5B5BD6',
        [int]$TabOrder = 0
    )
    if ($MeasureName) {
        $valueField = New-ExtensionMeasureField $Table $MeasureName
        $valueQueryRef = "$Table.$MeasureName"
        $nativeQueryRef = $MeasureName
    } else {
        $valueField = New-AggregationField $Table $ValueColumn 0
        $valueQueryRef = "Sum($Table.$ValueColumn)"
        $nativeQueryRef = "Sum of $ValueColumn"
    }
    $visual = @{
        '$schema' = $visualSchema
        name = $Name
        position = @{ x = $X; y = $Y; z = 0; width = $Width; height = $Height; tabOrder = $TabOrder }
        visual = @{
            visualType = 'clusteredBarChart'
            query = @{
                queryState = @{
                    Category = @{ projections = @(@{
                        field = New-ColumnField $Table $CategoryColumn
                        queryRef = "$Table.$CategoryColumn"
                        nativeQueryRef = $CategoryColumn
                    }) }
                    Y = @{ projections = @(@{
                        field = $valueField
                        queryRef = $valueQueryRef
                        nativeQueryRef = $nativeQueryRef
                    }) }
                }
                sortDefinition = @{
                    sort = @(@{ field = $valueField; direction = 'Descending' })
                    isDefaultSort = $true
                }
            }
            objects = @{
                dataPoint = @(@{
                    properties = @{ fill = New-SolidColor $Color }
                    selector = @{ metadata = $valueQueryRef }
                })
            }
            drillFilterOtherVisuals = $true
        }
    }
    return $visual
}

function New-Matrix {
    param(
        [string]$Name, [double]$X, [double]$Y, [double]$Width, [double]$Height,
        [string]$MeasureName, [int]$TabOrder = 0
    )
    $table = 'analysis_cross_pairs'
    $valueColumn = 'cooccurrence_post_count'
    $valueQueryRef = "$table.$MeasureName"
    $valueField = New-ExtensionMeasureField $table $MeasureName
    return @{
        '$schema' = $visualSchema
        name = $Name
        position = @{ x = $X; y = $Y; z = 0; width = $Width; height = $Height; tabOrder = $TabOrder }
        visual = @{
            visualType = 'pivotTable'
            query = @{
                queryState = @{
                    Rows = @{ projections = @(@{
                        field = New-ColumnField $table 'left_label'
                        queryRef = "$table.left_label"
                        nativeQueryRef = 'left_label'
                    }) }
                    Columns = @{ projections = @(@{
                        field = New-ColumnField $table 'right_label'
                        queryRef = "$table.right_label"
                        nativeQueryRef = 'right_label'
                    }) }
                    Values = @{ projections = @(@{
                        field = $valueField
                        queryRef = $valueQueryRef
                        nativeQueryRef = $MeasureName
                    }) }
                }
            }
            objects = @{
                columnHeaders = @(@{ properties = @{
                    columnAdjustment = New-Literal "'growToFit'"
                    autoSizeColumnWidth = New-Literal 'true'
                } })
            }
            visualContainerObjects = @{
                stylePreset = @(@{ properties = @{ name = New-Literal "'Minimal'" } })
            }
            drillFilterOtherVisuals = $true
        }
    }
}

function New-Page {
    param([string]$Name, [string]$DisplayName)
    return @{
        '$schema' = $pageSchema
        name = $Name
        displayName = $DisplayName
        displayOption = 'FitToPage'
        height = 1080
        width = 1920
        objects = @{
            background = @(@{ properties = @{
                color = New-SolidColor '#F7F8FC'
                transparency = New-Literal '0D'
            } })
        }
    }
}

function Add-Visual {
    param([string]$PageName, [hashtable]$Visual)
    $visualPath = Join-Path $pagesRoot "$PageName\visuals\$($Visual.name)\visual.json"
    Write-JsonFile $visualPath $Visual
}

$overviewPage = 'c9760c01050bb23d5d5d'
$goodsPage = '8a41d9e272ac4c9fb201'
$visualPage = 'c2d7b27f397a4f829a20'
$decisionPage = 'ec44c31728f44779b413'

Write-JsonFile (Join-Path $pagesRoot "$overviewPage\page.json") (New-Page $overviewPage '01 전체 인사이트')
Write-JsonFile (Join-Path $pagesRoot "$goodsPage\page.json") (New-Page $goodsPage '02 굿즈·소장 심층분석')
Write-JsonFile (Join-Path $pagesRoot "$visualPage\page.json") (New-Page $visualPage '03 시각적 매력 심층분석')
Write-JsonFile (Join-Path $pagesRoot "$decisionPage\page.json") (New-Page $decisionPage '04 차기 IP 선정 인사이트')

$pagesMetadata = @{
    '$schema' = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json'
    pageOrder = @($overviewPage, $goodsPage, $visualPage, $decisionPage)
    activePageName = $overviewPage
}
Write-JsonFile (Join-Path $pagesRoot 'pages.json') $pagesMetadata

# Page 1: executive overview
Add-Visual $overviewPage (New-TextBox 'f0018a12b6c9438e92a1' 70 42 1780 72 @('치이카와 인스타그램 데이터로 보는 차기 캐릭터 IP 성공 요인') '32px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 0)
Add-Visual $overviewPage (New-TextBox 'f00267f2d5594f45b3c2' 70 112 1780 38 @('정제 분석 표본 7,795건 · 다중 라벨 기반 평가영역 및 상품화 잠재력 분석') '16px' '#5F6368' 'Segoe UI' 'normal' 'left' 1)
Add-Visual $overviewPage (New-TextBox 'f003ba4d6de8498aa113' 70 178 390 130 @('12,534', '전체 게시물') '30px' '#5B5BD6' 'Segoe UI Semibold' 'bold' 'center' 2)
Add-Visual $overviewPage (New-TextBox 'f004e40ff2ac43ab9a70' 500 178 390 130 @('7,795', '정제 분석 게시물') '30px' '#5B5BD6' 'Segoe UI Semibold' 'bold' 'center' 3)
Add-Visual $overviewPage (New-TextBox 'f005f7821d0e40f5bc31' 930 178 390 130 @('36.88%', '굿즈·소장 언급률') '30px' '#D05A6E' 'Segoe UI Semibold' 'bold' 'center' 4)
Add-Visual $overviewPage (New-TextBox 'f00641387315467bb013' 1360 178 390 130 @('26.82%', '시각적 매력 언급률') '30px' '#D05A6E' 'Segoe UI Semibold' 'bold' 'center' 5)
Add-Visual $overviewPage (New-TextBox 'f007932dc8c845cc9011' 70 328 850 36 @('프로젝트 평가영역별 게시물 언급률') '21px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 6)
Add-Visual $overviewPage (New-Image 'f008e1784e0e4fb7a412' 70 374 850 545 'project_category_20261103.png' 7)
Add-Visual $overviewPage (New-TextBox 'f009de137bc84511a282' 970 328 850 36 @('형태소 키워드 언급 게시물 수') '21px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 8)
Add-Visual $overviewPage (New-BarChart 'f00a612df6d34e44a534' 970 374 850 545 'dim_keyword' 'keyword' 'post_count' '' '#D05A6E' 9)
Add-Visual $overviewPage (New-TextBox 'f00b4b134b7b42ae9301' 70 950 1750 70 @('해석 기준: 평가영역은 한 게시물이 여러 영역에 포함되는 다중 분류입니다. 2026년 수집량 집중과 판매·서비스 홍보 게시물의 영향을 고려해 빈도를 인과관계로 해석하지 않습니다.') '15px' '#5F6368' 'Segoe UI' 'normal' 'left' 10)

# Page 2: goods and ownership drilldown
Add-Visual $goodsPage (New-TextBox 'a101fe6f9a114b37aa01' 70 42 1780 70 @('굿즈·소장 심층분석: 무엇을, 어떻게 소비하는가') '32px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 0)
Add-Visual $goodsPage (New-TextBox 'a102c4d9a05f40219b02' 70 112 1780 38 @('분모: 굿즈·소장 게시물 2,875건 · 굿즈 유형과 소비 행동은 다중 분류') '16px' '#5F6368' 'Segoe UI' 'normal' 'left' 1)
Add-Visual $goodsPage (New-TextBox 'a103421f2bfb48d68903' 70 184 820 36 @('굿즈 유형 분포') '21px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 2)
Add-Visual $goodsPage (New-Image 'a104120c59154e55bc04' 70 230 820 380 'goods_type_20261103.png' 3)
Add-Visual $goodsPage (New-TextBox 'a105c1c495f644469d05' 970 184 820 36 @('소비·소장 행동 분포') '21px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 4)
Add-Visual $goodsPage (New-Image 'a1065ecbf1a44821a706' 970 230 820 380 'consumption_behavior_20261103.png' 5)
Add-Visual $goodsPage (New-TextBox 'a107232b673847d98007' 70 650 1220 36 @('굿즈 유형 × 소비·소장 행동 교차 매트릭스 (동시출현 게시물 수)') '21px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 6)
Add-Visual $goodsPage (New-Image 'a108533055a4475ba608' 70 700 1220 310 'goods_behavior_heatmap_20261103.png' 7)
Add-Visual $goodsPage (New-TextBox 'a1096a0ad88947bea909' 1340 650 470 300 @(
    '핵심 해석',
    '• 봉제·인형 36.3%, 피규어·완구 32.9%',
    '• 관심·탐색 31.7%, 구매·주문 30.1%',
    '• 랜덤·교환 28.1%로 반복구매 구조 확인',
    '• 차기 IP는 수집성뿐 아니라 실사용 확장성도 평가'
) '17px' '#202124' 'Segoe UI' 'normal' 'left' 8)

# Page 3: visual appeal drilldown
Add-Visual $visualPage (New-TextBox 'b201c9bf85b14f558201' 70 42 1780 70 @('시각적 매력 심층분석: 귀여움에서 행동으로') '32px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 0)
Add-Visual $visualPage (New-TextBox 'b202ee40328146a99b02' 70 112 1780 38 @('분모: 시각적 매력 게시물 2,091건 · 시각 요소와 반응의 연결 구조') '16px' '#5F6368' 'Segoe UI' 'normal' 'left' 1)
Add-Visual $visualPage (New-TextBox 'b203ea5d06194ddbaa03' 70 184 780 36 @('시각적 매력 요소') '21px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 2)
Add-Visual $visualPage (New-Image 'b204952d366f44718104' 70 230 780 350 'visual_element_20261103.png' 3)
Add-Visual $visualPage (New-TextBox 'b205461770724c739b05' 920 184 780 36 @('시각적 매력에 연결된 반응') '21px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 4)
Add-Visual $visualPage (New-Image 'b206158a16ca4edb9c06' 920 230 780 350 'visual_reaction_20261103.png' 5)
Add-Visual $visualPage (New-TextBox 'b2071aac35534f70aa07' 70 620 1220 36 @('시각 요소 × 반응 교차 매트릭스 (동시출현 게시물 수)') '21px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 6)
Add-Visual $visualPage (New-Image 'b2081a12f60645969008' 70 670 1220 340 'visual_reaction_heatmap_20261103.png' 7)
Add-Visual $visualPage (New-TextBox 'b2093cb34844492eb909' 1340 620 480 350 @(
    '변별 포인트',
    '• 귀여움·사랑스러움 93.5%: 기본 진입 조건',
    '• 표정·얼굴 → 촬영·공유 49.5%',
    '• 형태·디자인 → 소유·구매 욕구 41.6%',
    '• 색감·배색 → 소유·구매 욕구 53.5%',
    '• 구체적 디자인 이유 언급 여부를 차기 IP 변별 지표로 사용'
) '17px' '#202124' 'Segoe UI' 'normal' 'left' 8)

# Page 4: decision framework
Add-Visual $decisionPage (New-TextBox 'c301173e33404daf9301' 70 42 1780 70 @('차기 국내 창작자 IP 선정 인사이트') '32px' '#24245E' 'Segoe UI Semibold' 'bold' 'left' 0)
Add-Visual $decisionPage (New-TextBox 'c302b72ba09a41049202' 70 112 1780 38 @('치이카와 데이터에서 확인된 성공 요인을 후보 IP의 공통 평가기준으로 전환') '16px' '#5F6368' 'Segoe UI' 'normal' 'left' 1)
Add-Visual $decisionPage (New-TextBox 'c30376087f424865a303' 90 210 520 650 @(
    '1. 시각적 매력',
    '귀여움은 진입 조건, 표정·실루엣·색감의 차별성을 평가',
    '',
    '2. 상품화 잠재력',
    '굿즈 유형 다양성, 재현도, 실사용 확장성을 평가',
    '',
    '3. 반복구매 구조',
    '수집·랜덤·교환·한정판이 지속 수요로 이어지는지 확인'
) '19px' '#202124' 'Segoe UI' 'normal' 'left' 2)
Add-Visual $decisionPage (New-TextBox 'c3046f751a8d4445a404' 700 210 520 650 @(
    '4. 정서·스토리 연결',
    '공감·힐링과 세계관·캐릭터 관계가 함께 언급되는지 확인',
    '',
    '5. 오프라인 확장성',
    '팝업·카페·전시 등 현장 경험으로 확장 가능한지 평가',
    '',
    '6. 협업·확산성',
    '브랜드 콜라보와 팬 창작이 자연스럽게 발생하는지 확인'
) '19px' '#202124' 'Segoe UI' 'normal' 'left' 3)
Add-Visual $decisionPage (New-TextBox 'c30567436e844949a505' 1310 210 520 650 @(
    '의사결정 원칙',
    '• 모든 후보 IP에 동일한 기간·수집어·정제 규칙 적용',
    '• 절대 빈도보다 언급률·동시출현·향상도를 함께 확인',
    '• 광고·판매·공식계정과 소비자 반응을 분리',
    '• 이벤트 피크와 장기 기준선을 구분',
    '• 표본 검수로 분류 사전과 감성 규칙을 보정'
) '19px' '#202124' 'Segoe UI' 'normal' 'left' 4)
Add-Visual $decisionPage (New-TextBox 'c306970fbfb342928606' 90 900 1740 100 @('주의: 인스타그램 게시물 빈도와 동시출현은 실제 구매전환이나 인과관계를 의미하지 않습니다. 계정·노출·팔로워 정보가 없으므로 반응 수는 보조지표로 사용하고, 국내 후보 IP 비교 시 같은 수집·정제 파이프라인을 적용해야 합니다.') '16px' '#8A3B4A' 'Segoe UI Semibold' 'bold' 'left' 5)

# Package the seven precomputed analysis charts as native Power BI image visuals.
# This removes all failing query/filter/extension-measure dependencies.
$staticChartRoot = 'C:\Users\user\Desktop\KDT_2026\프로젝트\02_데이터_프로젝트\03_code\04_PowerBI\.pbix_work_20261103\static_charts'
$registeredRoot = Join-Path $reportRoot 'StaticResources\RegisteredResources'
New-Item -ItemType Directory -Path $registeredRoot -Force | Out-Null
$imageMap = [ordered]@{
    'project_category.png' = 'project_category_20261103.png'
    'goods_type.png' = 'goods_type_20261103.png'
    'consumption_behavior.png' = 'consumption_behavior_20261103.png'
    'goods_behavior_heatmap.png' = 'goods_behavior_heatmap_20261103.png'
    'visual_element.png' = 'visual_element_20261103.png'
    'visual_reaction.png' = 'visual_reaction_20261103.png'
    'visual_reaction_heatmap.png' = 'visual_reaction_heatmap_20261103.png'
}
foreach ($sourceName in $imageMap.Keys) {
    Copy-Item -LiteralPath (Join-Path $staticChartRoot $sourceName) -Destination (Join-Path $registeredRoot $imageMap[$sourceName]) -Force
}

$reportConfigPath = Join-Path $definitionRoot 'report.json'
$reportConfig = Get-Content -Raw -LiteralPath $reportConfigPath | ConvertFrom-Json -AsHashtable
$basePackages = @($reportConfig.resourcePackages | Where-Object { $_.name -ne 'RegisteredResources' })
$registeredPackage = @{
    name = 'RegisteredResources'
    type = 'RegisteredResources'
    items = @($imageMap.Values | ForEach-Object { @{ name = $_; path = $_; type = 'Image' } })
}
$reportConfig.resourcePackages = @($basePackages) + @($registeredPackage)
Write-JsonFile $reportConfigPath $reportConfig

$extensionPath = Join-Path $definitionRoot 'reportExtensions.json'
if (Test-Path -LiteralPath $extensionPath) {
    Remove-Item -LiteralPath $extensionPath -Force
}

# Temporary PBIP metadata used only by the validator. These files are excluded when repackaging the PBIX.
$platform = @{
    '$schema' = 'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json'
    metadata = @{ type = 'Report'; displayName = 'Integral_instagram' }
    config = @{ version = '2.0'; logicalId = '1ebfbc64-d745-4ab2-9cb3-3982e070f0a1' }
}
$definitionPbir = @{
    '$schema' = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json'
    version = '4.0'
    datasetReference = @{ byPath = @{ path = '../Integral_instagram.SemanticModel' } }
}
Write-JsonFile (Join-Path $reportRoot '.platform') $platform
Write-JsonFile (Join-Path $reportRoot 'definition.pbir') $definitionPbir

Write-Output 'PBIR report definition generated.'
