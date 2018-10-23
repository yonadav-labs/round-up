$(function () {
        $('#id_start_date_picker').datetimepicker();
        $('#id_end_date_picker').datetimepicker({
            useCurrent: false //Important! See issue #1075
        });
        $("#id_start_date_picker").on("dp.change", function (e) {
            $('#id_end_date_picker').data("DateTimePicker").minDate(e.date);
        });
        $("#id_end_date_picker").on("dp.change", function (e) {
            $('#id_start_date_picker').data("DateTimePicker").maxDate(e.date);
        });
    });