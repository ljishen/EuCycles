{% macro _size2kb(size) -%}
    {% set sz_kb = size | regex_replace('[^0-9]') | int -%}
    {% if size | regex_search('[mM]') -%}
        {% set sz_kb = sz_kb * (2 ** 10) -%}
    {% elif size | regex_search('[gG]') -%}
        {% set sz_kb = sz_kb * (2 ** 20) -%}
    {% endif -%}
    {{ caller(sz_kb) }}
{%- endmacro -%}

['{{ blocksize }}'
{%- call(blk_sz_kb) _size2kb(blocksize) -%}
    {% for size in transmission_sizes -%}
        {% call(sz_kb) _size2kb(size) -%}
            {% if sz_kb > blk_sz_kb -%}
                , '{{ size }}'
            {%- endif -%}
        {% endcall -%}
    {% endfor -%}
{% endcall -%}
]
