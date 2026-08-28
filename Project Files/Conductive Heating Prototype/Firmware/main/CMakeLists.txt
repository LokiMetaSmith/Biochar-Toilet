idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES
        esp_adc
        esp_timer
        freertos
        log
        spi_flash
        led_strip
    PRIV_REQUIRES
        driver
)
