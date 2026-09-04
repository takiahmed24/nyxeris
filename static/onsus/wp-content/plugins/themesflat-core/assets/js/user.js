(function( $ ) {
	'use strict';
    var tfre_login = function () {
        $('#tfre_custom-login-form').on('submit', function (e) {
            e.preventDefault();
            $('.tfre_login-form').validate({
                errorElement: "span",
                rules: {
                    username: {
                        required: true,
                        minlength: 3
                    },
                    password: {
                        required: true
                    },
                },
                messages: {
                    username: "",
                    password: "",
                }
            });
            var form = $(this);
            var formData = form.serialize();
            var $messages = $(this).parents('.tfre_login-form').find('.tfre_message');
    
            if (form.valid()) {
                $.ajax({
                    type: 'POST',
                    url: ajax_object.ajaxUrl,
                    data: formData + '&action=custom_login&security=' + ajax_object.nonce,
                    beforeSend: function () {
                        $messages.empty().append('<span class="success text-success"> Loading </span>');
                    },
                    success: function (response) {
                        // Handle the registration success response
                        if (response.status) {
                            window.location.href = response.redirect_url;
                        } else {
                            $messages.empty().append('<span class="error text-danger"><i class="fa fa-close"></i> ' + response.message + '</span>');
                        }
                    },
                    error: function (xhr, status, error) {
                        // Handle the registration error response
                        console.log(error);
                    }
                });
            }
        });
    }
    var tfre_register = function () {
        $('#tfre_custom-register-form').on('submit', function (e) {
            e.preventDefault();
            $('.tfre_registration-form').validate({
                errorElement: "span",
                rules: {
                    username: {
                        required: true,
                        minlength: 3
                    },
                    email: {
                        required: true,
                        pattern: /^[\w\-\.\+]+\@[a-zA-Z0-9\.\-]+\.[a-zA-z0-9]{2,10}$/
                    },
                    password: {
                        required: true
                    },
                    confirm_password: {
                        required: true
                    }
                },
                messages: {
                    username: "",
                    email: "",
                    password: "",
                    confirm_password: ""
                }
            });
            var form = $(this);
            var formData = form.serialize();
            var $messages = $(this).parents('.tfre_registration-form').find('.tfre_message');
            if (form.valid()) {
                $.ajax({
                    type: 'POST',
                    url: ajax_object.ajaxUrl,
                    data: formData + '&action=custom_register&security=' + ajax_object.nonce,
                    beforeSend: function () {
                        $messages.empty().append('<span class="success text-success"> Loading </span>');
                    },
                    success: function (response) {
                        // Handle the registration success response
                        if (response.status) {
                            $messages.empty().append('<span class="success text-success"><i class="fa fa-check"></i> ' + response.message + '</span>');

                            setTimeout(() => {
                                window.location.reload();
                            }, 1000);
    
                        } else {
                            $messages.empty().append('<span class="error text-danger"><i class="fa fa-close"></i> ' + response.message + '</span>');
                        }
                    },
                    error: function (xhr, status, error) {
                        // Handle the registration error response
                        console.log(error);
                    }
                });
            }
        });
    }


    var tfre_show_register_login_modal = function () {
        // class display-pop-login is custom class in Appearance menu
        $('.sign-in').on('click', function () {
            $("#tfre_login_register_modal").modal('show');
            tfre_reset_login_modal();
        });
    }
    var tfre_reset_login_modal = function () {
        var registerTab = document.getElementById('tfre_register_tab');
        var loginTab = document.getElementById('tfre_login_tab');
        var resetWrap = document.getElementById('tfre-reset-password-wrap');
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
        resetWrap.style.display = "none";
    }

    var tfre_redirect_login = function () {
        var registerTab = document.getElementById('tfre_register_tab');
        var loginTab = document.getElementById('tfre_login_tab');
        var resetWrap = document.getElementById('tfre-reset-password-wrap');
        $('.tfre_login_redirect').on('click', function () {
            loginTab.classList.add('active');
            registerTab.classList.remove('active');
            resetWrap.style.display = "none";
        });

        $('#tfre_register_redirect').on('click', function () {
            registerTab.classList.add('active');
            loginTab.classList.remove('active');
            resetWrap.style.display = "none";
            
        });

        $('#tfre-reset-password').on('click', function () {
            resetWrap.style.display = "block";
            registerTab.classList.remove('active');
            loginTab.classList.remove('active');
        });
    }
    var tfre_reset_password = function() {
        $('.tfre_forgetpass').on('click',function (e) {
            e.preventDefault();
            var $form = $(this).parents('form');
            $.ajax({
                type: 'post',
                url: ajax_object.ajaxUrl,
                dataType: 'json',
                data: $form.serialize(),
                beforeSend: function () {
                    $('.tfre_messages_reset_password').empty().append('<span class="success text-success"> Loading </span>');
                },
                success: function (response) {
                    if (response.success) {
                        $('.tfre_messages_reset_password').empty().append('<span class="success text-success"><i class="fa fa-check"></i> ' + response.message + '</span>');
                    } else {
                        $('.tfre_messages_reset_password').empty().append('<span class="error text-danger"><i class="fa fa-close"></i> ' + response.message + '</span>');
                    }
                }
            });
        });
    }

    
    jQuery(document).ready(function ($) {
        tfre_login();
        tfre_register();
        tfre_show_register_login_modal();
        tfre_redirect_login();
        tfre_reset_password();
    })
})( jQuery );


