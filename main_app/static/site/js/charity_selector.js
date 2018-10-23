function toggle_switch(id, switch_elem, to_state, api_src, csrftoken) {
        $('#switch-'+id).hide();
        $("#loading-icon-"+id).removeClass( "loader-fa-icon-hide" );

        //Show a loading thing
        // Send AJAX form serialized to view
        $.ajax({

            //store_url=request.user.store_url_str
            url : api_src,
            type : "POST", // http method
            data: {
                csrfmiddlewaretoken: csrftoken,
                to_state: to_state
            },
            // handle a successful response
            success : function(json) {

                $('#switch-'+id).show();

                if (to_state === 'off') {
                    // Change the text and tag color of the current charity div
                    $('#charity-label').text(json.charity_name)
                    $("#loading-icon-"+id).addClass( "loader-fa-icon-hide" );
                }
                else if (to_state === 'on') {
                    // Change the text and tag color of the current charity div
                    $('#charity-label').text(json.charity_name)

                    $("#loading-icon-"+id).addClass( "loader-fa-icon-hide" );
                    // For each switch ensure buttons are disabled
                    $('.checkbox-slider').each(function( index, value ) {
                        var ch = $(this), c;

                        // Deselect the switch
                        if (ch.val() !== id) {
                            if (ch.is(':checked')) {
                                ch.prop('checked', false);
                            }
                        }

                    });
                }
                $("#overlay").hide();
                // Alert the user of the response
                ShopifyApp.flashNotice(json.message);
            },
            // handle a non-successful response
            error : function(xhr,errmsg,err) {
                if (xhr == null || xhr.responseJSON == null ) {
                      $("#loading-icon-"+id).removeClass( "fa-circle-o-notch" );
                      $("#loading-icon-"+id).removeClass( "fa-spin" );
                      $("#loading-icon-"+id).addClass( "fa-exclamation-circle red" );
                      // Alert the user of the response
                      $("#overlay").hide();
                      ShopifyApp.flashError("An unknown error occurred.");
                }
                else {
                    // Alert the user of the response
                      $("#loading-icon-"+id).removeClass( "fa-circle-o-notch" );
                      $("#loading-icon-"+id).removeClass( "fa-spin" );
                      $("#loading-icon-"+id).addClass( "fa-exclamation-circle red" );
                      $("#overlay").hide();
                      ShopifyApp.flashError(xhr.responseJSON.message);
                }
            }
        });
    };

    // using jQuery get the Django CSRF token from cookies
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

        //After hide a loading thing
    $(function() {

        var csrftoken = getCookie('csrftoken');

        // Register handler for checkbox clicks
        $('.checkbox-slider').change(function() {
            var ch = $(this), c;
            // The id we will act on
            var context_id = ch.val();
            var api_src = ch.data('api-src');

            if (ch.is(':checked')) {
                ch.prop('checked', false);
                ShopifyApp.Modal.confirm({
                      title: "Select Charity?",
                      message: "Are you sure you want to select this charity?",
                      okButton: "Yes, I'm sure",
                      cancelButton: "No"
                }, function(result){
                  if(result){
                    ch.prop('checked', true);
                    $("#overlay").show();
                    // Call an Ajax request to change status and trigger sync.\
                    toggle_switch(context_id, $(this).closest('.switch'), 'on', api_src, csrftoken)
                  }
                });
            } else {
                ch.prop('checked', true);

                ShopifyApp.Modal.confirm({
                      title: "Deselect Charity?",
                      message: "Are you sure you want to deselect this charity?",
                      okButton: "Yes, I'm sure",
                      cancelButton: "Cancel",
                      style: "danger"
                }, function(result){
                  if(result){
                    ch.prop('checked', false);
                    $("#overlay").show();
                    // Call an Ajax request to change status and trigger sync.\
                    toggle_switch(context_id, $(this).closest('.switch'), 'off', api_src, csrftoken)
                  }
                });
            }
        });
    });